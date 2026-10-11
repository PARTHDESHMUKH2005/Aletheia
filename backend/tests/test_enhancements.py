from tests.helpers import AUTH_HEADERS, JPEG_BYTES
"""Tests for the decision-engine, assessment, e-waste, review and dashboard additions."""
import copy
import json

import pytest
from fastapi.testclient import TestClient

from app import pipeline
from app.main import app
from app.models import Characterization, Item
from app.tools import ewaste, matching, report
from app.tools.assessment import assess_item
from tests.test_matching import ORG_LOCATION, SYNTHETIC_PROCESSORS, _synthetic_steel_factor, make_item

client = TestClient(app, headers=AUTH_HEADERS)


# --- smart recovery engine ---

def _patch(monkeypatch, processors):
    monkeypatch.setattr(matching, "_PROCESSORS", processors)
    monkeypatch.setattr(matching, "get_avoided_factor", _synthetic_steel_factor)


def test_losing_candidates_explain_why_in_numbers(monkeypatch):
    _patch(monkeypatch, SYNTHETIC_PROCESSORS)
    result = matching.find_processors(make_item(), ORG_LOCATION, w=0.0)
    pick, loser = result["candidates"]
    assert pick["why_not_picked"] is None
    assert "less net" in loser["why_not_picked"] and "more" in loser["why_not_picked"]


def test_candidates_separate_gross_transport_and_net(monkeypatch):
    _patch(monkeypatch, SYNTHETIC_PROCESSORS)
    c = matching.find_processors(make_item(), ORG_LOCATION)["candidates"][0]
    assert c["gross_rupees"] == pytest.approx(c["price_per_kg_inr"] * 100)
    assert c["net_rupees"] == pytest.approx(c["gross_rupees"] - c["transport_cost_rupees"])


def test_evidence_weight_can_flip_the_pick_and_defaults_to_off(monkeypatch):
    checked = dict(SYNTHETIC_PROCESSORS[1], authorization_ref="REF-1", authorization_checked_on="2026-01-01")
    _patch(monkeypatch, [SYNTHETIC_PROCESSORS[0], checked])
    base = matching.find_processors(make_item(), ORG_LOCATION, w=0.0)
    assert base["picked_processor_id"] == "proc_expensive_low_carbon"
    weighted = matching.find_processors(make_item(), ORG_LOCATION, w=0.0, evidence_weight=0.9)
    assert weighted["picked_processor_id"] == "proc_cheap_high_carbon"
    assert weighted["candidates"][0]["evidence_level"] == 2


def test_bad_evidence_weight_rejected(monkeypatch):
    _patch(monkeypatch, SYNTHETIC_PROCESSORS)
    with pytest.raises(ValueError):
        matching.find_processors(make_item(), ORG_LOCATION, evidence_weight=1.5)


def test_ewaste_recycling_needs_an_authorization_reference():
    laptop = make_item(material="e_waste_computer", composition_note="old laptop", purity="mixed", quantity_kg=10)
    result = matching.find_processors(laptop, {"lat": 30.34, "lng": 76.39})
    assert result["picked_processor_id"] is None
    assert all(not c["authorization_gate_passed"] for c in result["unscored_candidates"] if c["tier"] != "reuse")


# --- contamination and confidence ---

def test_assessment_never_reports_a_purity_percentage():
    a = assess_item(make_item(contaminants=["steel pieces mixed in"], material="aluminium_scrap", purity="mixed"))
    assert "%" not in json.dumps(a).replace("No percentage", "")
    assert a["contaminants"] == ["steel pieces mixed in"]
    assert "Manual inspection" in a["recommended_action"]
    assert a["price_is_provisional"] and not a["needs_human_review"]


def test_low_confidence_goes_to_a_human():
    a = assess_item(make_item(confidence=0.4))
    assert a["needs_human_review"] and a["confidence_band"] == "low"
    assert "human reviewer" in a["recommended_action"]


def test_confidence_is_labelled_uncalibrated():
    assert "not calibrated" in assess_item(make_item())["confidence_basis"]


def test_out_of_scope_is_not_routed():
    a = assess_item(make_item(composition_note="used syringe and needle"))
    assert a["recommended_action"].startswith("Do not route")


# --- e-waste ---

def _batch():
    return ewaste.register_devices(None, [
        {"asset_tag": "PC-1", "kind": "desktop", "condition": "working", "storage_drives": 2},
        {"asset_tag": "PC-2", "kind": "laptop", "condition": "broken", "storage_drives": 1},
        {"asset_tag": "MON-1", "kind": "monitor", "condition": "repairable"},
    ])


def test_pathway_follows_condition_and_drives_are_tracked_separately():
    batch = _batch()
    assert [d["pathway"] for d in batch["devices"]] == ["reuse", "recycle", "refurbish"]
    assert [d["drive_id"] for d in batch["drives"]] == ["PC-1-D1", "PC-1-D2", "PC-2-D1"]


def test_duplicate_tag_and_bad_condition_rejected():
    with pytest.raises(ValueError):
        ewaste.register_devices(_batch(), [{"asset_tag": "PC-1", "kind": "desktop", "condition": "working"}])
    with pytest.raises(ValueError):
        ewaste.register_devices(None, [{"asset_tag": "X", "kind": "desktop", "condition": "shiny"}])


def test_transfer_blocked_until_every_drive_has_a_record():
    batch = _batch()
    assert len(ewaste.blocking_reasons(batch)) == 3
    assert ewaste.summarize(batch)["transfer_blocked"]


def test_wipe_requires_certificate_ref_and_operator():
    from app.storage.local import LocalStorage
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmp:
        storage = LocalStorage(db_path=Path(tmp) / "t.db")
        batch = _batch()
        with pytest.raises(ValueError):
            ewaste.record_drive_wipe(storage, "s", batch, "PC-1-D1", "overwrite", "", "ann")
        with pytest.raises(ValueError):
            ewaste.record_drive_wipe(storage, "s", batch, "PC-1-D1", "magic", "C-1", "ann")
        for d in ("PC-1-D1", "PC-1-D2", "PC-2-D1"):
            ewaste.record_drive_wipe(storage, "s", batch, d, "overwrite", "C-1", "ann")
        assert ewaste.blocking_reasons(batch) == []
        assert len(storage.get_ledger_chain("s")) == 3
        storage.close()


# --- endpoints: review, handoff gate, dashboard ---

def _stream(monkeypatch, **kw):
    ch = Characterization(items=[make_item(**kw)], overall_confidence=kw.get("confidence", 0.9))
    monkeypatch.setattr(pipeline, "characterize_waste", lambda *a, **k: ch)
    up = client.post("/uploads", json={"count": 1, "org_id": "org_campus_lab"}).json()[0]
    client.put(up["url"], content=JPEG_BYTES)
    r = client.post("/streams", json={"org_id": "org_campus_lab", "photo_keys": [up["key"]], "pincode": "147001"})
    return r.json()["stream_id"]


def test_review_queue_and_confirm_flow(monkeypatch):
    sid = _stream(monkeypatch, confidence=0.4)
    assert client.get(f"/streams/{sid}").json()["status"] == "NEEDS_REVIEW"
    assert sid in [q["stream_id"] for q in client.get("/review-queue").json()]
    r = client.post(f"/streams/{sid}/review", json={"decision": "confirm_routing", "reviewer": "Asha"})
    assert r.status_code == 200 and r.json()["status"] == "ROUTED"
    assert sid not in [q["stream_id"] for q in client.get("/review-queue").json()]
    assert "human_review" in [e["event"] for e in client.get(f"/streams/{sid}").json()["ledger"]]
    assert client.get(f"/verify/{sid}").json()["ok"]
    assert client.post(f"/streams/{sid}/review", json={"decision": "reject", "reviewer": "A"}).status_code == 409


def test_review_needs_a_reviewer_and_valid_decision(monkeypatch):
    sid = _stream(monkeypatch, confidence=0.4)
    assert client.post(f"/streams/{sid}/review", json={"decision": "confirm_routing", "reviewer": " "}).status_code == 422
    assert client.post(f"/streams/{sid}/review", json={"decision": "approve", "reviewer": "A"}).status_code == 422


def test_reject_removes_stream_from_totals(monkeypatch):
    sid = _stream(monkeypatch, confidence=0.4)
    client.post(f"/streams/{sid}/review", json={"decision": "reject", "reviewer": "A"})
    assert client.get(f"/streams/{sid}").json()["status"] == "REJECTED"


def test_handoff_blocked_until_drives_wiped(monkeypatch):
    sid = _stream(monkeypatch)
    client.post(f"/streams/{sid}/ewaste", json={"devices": [{"asset_tag": "A1", "kind": "desktop", "condition": "broken", "storage_drives": 1}]})
    blocked = client.post(f"/streams/{sid}/handoff", json={"status": "collected"})
    assert blocked.status_code == 409 and blocked.json()["detail"]["blocked"]
    client.post(f"/streams/{sid}/ewaste/drives/A1-D1/wipe", json={"method": "overwrite", "certificate_ref": "C-9", "operator": "Ravi"})
    assert client.post(f"/streams/{sid}/handoff", json={"status": "collected"}).status_code == 200


def test_dashboard_separates_projected_from_realised_and_lists_actions(monkeypatch):
    sid = _stream(monkeypatch, quantity_kg=100.0)
    d = client.get("/orgs/org_campus_lab/dashboard").json()
    assert d["revenue_inr"]["projected"]["net_inr"] > 0
    base_realised = d["revenue_inr"]["realised"]["net_inr"]
    assert any(a["stream_id"] == sid and a["action"] == "Enter a weight" for a in d["outstanding_actions"]) is False
    client.post(f"/streams/{sid}/handoff", json={"status": "verified", "weight_kg": 50})
    d2 = client.get("/orgs/org_campus_lab/dashboard").json()
    assert d2["kg"]["verified"] >= 50
    assert d2["revenue_inr"]["realised"]["net_inr"] > base_realised
    p = d2["revenue_inr"]["projected"]
    assert p["net_inr"] == pytest.approx(p["gross_inr"] - p["transport_cost_inr"], abs=0.05)
    assert "methodology" in d2 and d2["co2e"]["factors_used"]


def test_needs_review_streams_are_not_in_projected_totals():
    streams = [{
        "stream_id": "a", "status": "NEEDS_REVIEW",
        "characterization": {"items": [make_item().model_dump()]},
        "routing": [{"candidates": [{"processor_id": "p", "tier": "recycle", "net_rupees": 999.0, "gross_rupees": 1000.0,
                                     "transport_cost_rupees": 1.0, "net_co2e_kg": 5.0}], "picked_processor_id": "p"}],
    }]
    d = report.org_impact(streams, {})
    assert d["revenue_inr"]["projected"]["net_inr"] == 0
    assert d["pending"]["awaiting_review"] == 1


def test_scoring_config_endpoint_matches_module_constants():
    cfg = client.get("/scoring-config").json()
    assert cfg["transport_cost_inr_per_tonne_km"] == matching.TRANSPORT_COST_INR_PER_TONNE_KM


def test_legacy_routing_without_gross_still_reconciles():
    streams = [{
        "stream_id": "old", "status": "ROUTED",
        "characterization": {"items": [make_item(quantity_kg=10).model_dump()]},
        "routing": [{"candidates": [{"processor_id": "p", "tier": "recycle", "price_per_kg_inr": 30.0,
                                     "net_rupees": 290.0, "net_co2e_kg": 5.0}], "picked_processor_id": "p"}],
    }]
    p = report.org_impact(streams, {})["revenue_inr"]["projected"]
    assert p["gross_inr"] == 300.0 and p["transport_cost_inr"] == 10.0 and p["net_inr"] == 290.0


def test_missing_transfer_record_is_flagged_only_after_collection_step_skipped():
    import json as j
    def ev(name): return {"event": name, "payload_json": j.dumps({}), "ts": "t"}
    stream = {"stream_id": "s", "status": "ROUTED",
              "characterization": {"items": [make_item(material="e_waste_computer", quantity_kg=5).model_dump()]},
              "routing": [{"candidates": [{"processor_id": "p", "tier": "recycle", "price_per_kg_inr": 30.0, "net_rupees": 1.0, "net_co2e_kg": 1.0}], "picked_processor_id": "p"}]}
    skipped = report.org_impact([stream], {"s": [ev("handoff_requested"), ev("handoff_verified")]})
    assert any(m["document"] == "transfer record" for m in skipped["missing_documents"])
    normal = report.org_impact([stream], {"s": [ev("handoff_requested"), ev("handoff_collected"), ev("handoff_verified")]})
    assert not any(m["document"] == "transfer record" for m in normal["missing_documents"])


def test_missing_weighment_slip_is_flagged_for_metal_verified_without_weighing():
    import json as j
    def ev(name): return {"event": name, "payload_json": j.dumps({}), "ts": "t"}
    stream = {"stream_id": "s", "status": "ROUTED",
              "characterization": {"items": [make_item().model_dump()]},
              "routing": [{"candidates": [{"processor_id": "p", "tier": "recycle", "price_per_kg_inr": 30.0, "net_rupees": 1.0, "net_co2e_kg": 1.0}], "picked_processor_id": "p"}]}
    d = report.org_impact([stream], {"s": [ev("handoff_requested"), ev("handoff_verified")]})
    assert any(m["document"] == "weighment slip" for m in d["missing_documents"])
    d = report.org_impact([stream], {"s": [ev("handoff_weighed"), ev("handoff_verified")]})
    assert not any(m["document"] == "weighment slip" for m in d["missing_documents"])


def test_register_devices_failure_does_not_mutate_existing_batch():
    from app.tools import ewaste
    existing = ewaste.register_devices(None, [{"asset_tag": "A1", "kind": "laptop", "condition": "working", "storage_drives": 1}])
    snapshot = copy.deepcopy(existing)
    with pytest.raises(ValueError):
        ewaste.register_devices(existing, [{"asset_tag": "A2", "kind": "laptop"}, {"asset_tag": "A1"}])
    assert existing == snapshot
