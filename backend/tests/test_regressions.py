"""End-to-end regressions for routing, authorization, integrity and input validation."""
import json
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from pypdf import PdfReader
from PIL import Image

from app import auth, main, pipeline
from app.config import get_storage, get_settings
from app.models import Characterization, Item, StreamCreateRequest
from app.tools import characterize, ledger, report
from strands.types.exceptions import MaxTokensReachedException
from tests.helpers import AUTH_HEADERS, JPEG_BYTES
from tests.test_matching import make_item


@pytest.fixture
def runtime(monkeypatch):
    storage = get_storage()
    monkeypatch.setattr(main, "_storage", lambda: storage)
    monkeypatch.setattr(auth, "get_storage", lambda: storage)
    def seed(sid="sample", items=None, org_id="org_campus_workshop"):
        items = items if items is not None else [make_item(quantity_basis="stated")]
        photo_key = f"{org_id}/{sid}-photo.jpg"
        storage.save_upload(photo_key, JPEG_BYTES)
        storage.create_stream(sid, {"org_id": org_id, "status": "SUBMITTED", "pincode": "147001",
            "photo_keys": [photo_key], "slider_w": 0.5})
        monkeypatch.setattr(pipeline, "characterize_waste", lambda *a, **kw:
            Characterization(items=items, overall_confidence=0.9))
        pipeline.run_pipeline(sid, storage)
        return sid
    return storage, TestClient(main.app, headers=AUTH_HEADERS), seed


def test_authentication_and_organization_boundaries(runtime):
    storage, admin, seed = runtime
    seed("workshop")
    seed("lab", org_id="org_campus_lab")
    anonymous = TestClient(main.app)
    workshop = TestClient(main.app, headers={"Authorization": "Bearer test-workshop-operator-credential"})
    assert anonymous.get("/streams/workshop").status_code == 401
    assert workshop.get("/streams/workshop").status_code == 200
    for path in ("/streams/lab", "/streams/lab/report", "/streams/lab/ewaste",
                 "/orgs/org_campus_lab/dashboard", "/local-uploads/org_campus_lab/photo.jpg"):
        assert workshop.get(path).status_code == 403
    assert workshop.post("/streams/workshop/review", json={"decision": "reject", "reviewer": "Someone"}).status_code == 403
    assert workshop.post("/streams/workshop/wipe", json={}).status_code == 403
    assert workshop.post("/dev/tamper/workshop").status_code == 403
    assert anonymous.get("/verify/workshop").json()["ok"]
    assert anonymous.get("/processors").status_code == 200
    assert workshop.get("/session").json()["orgs"][0]["id"] == "org_campus_workshop"


def test_credential_configuration_fails_closed(runtime, monkeypatch):
    _, client, _ = runtime
    monkeypatch.delenv("API_TOKENS_JSON", raising=False)
    assert client.get("/session").status_code == 503
    monkeypatch.setenv("API_TOKENS_JSON", "malformed")
    assert client.get("/session").status_code == 503


def test_review_queue_only_returns_permitted_organizations(runtime):
    _, _, seed = runtime
    seed("workshop-review", [make_item(confidence=0.4)])
    seed("lab-review", [make_item(confidence=0.4)], org_id="org_campus_lab")
    client = TestClient(main.app, headers={"Authorization": "Bearer test-lab-reviewer-credential"})
    assert [row["stream_id"] for row in client.get("/review-queue").json()] == ["lab-review"]
    assert client.get("/review-queue?org_id=org_campus_workshop").status_code == 403


@pytest.mark.parametrize("field,value", [("event", "data_wipe_confirmed"), ("ts", "changed"),
                                        ("hash_version", 1), ("link_no", 99)])
def test_every_ledger_metadata_field_is_protected(runtime, field, value):
    storage, client, seed = runtime
    seed()
    storage._conn.execute(f"UPDATE ledger SET {field}=? WHERE chain_id=?", (value, "sample"))
    storage._conn.commit()
    assert not client.get("/verify/sample").json()["ok"]
    assert client.post("/streams/sample/handoff", json={"status": "verified"}).status_code == 409


def test_ledger_cannot_be_relocated_to_another_chain(runtime):
    storage, _, seed = runtime
    seed()
    storage._conn.execute("UPDATE ledger SET chain_id='copied' WHERE chain_id='sample'")
    storage._conn.commit()
    assert not ledger.verify(storage, "copied")["ok"]


def test_unknown_and_empty_records_are_not_verified(runtime):
    storage, client, _ = runtime
    assert client.get("/verify/does-not-exist").status_code == 404
    storage.create_stream("empty", {"org_id": "org_campus_workshop", "status": "SUBMITTED"})
    assert client.get("/verify/empty").json() == {"ok": False, "links": 0, "first_broken": None}


def test_slider_choice_is_saved_and_used_by_passport_handoff_and_dashboard(runtime):
    storage, client, seed = runtime
    seed()
    original = client.get("/streams/sample").json()["routing"][0]["picked_processor_id"]
    preview = client.get("/streams/sample/route?w=1").json()
    assert preview["routing"]["picked_processor_id"] != original
    assert client.get("/streams/sample").json()["routing"][0]["picked_processor_id"] == original
    saved = client.put("/streams/sample/route", json={"w": 1, "item_index": 0}).json()
    stream = client.get("/streams/sample").json()
    assert stream["routing"][0] == saved["routing"]
    assert stream["receipts"][0] == saved["receipt"]
    assert client.post("/streams/sample/handoff", json={"status": "verified", "weight_kg": 100}).status_code == 200
    event = json.loads(storage.get_ledger_head("sample")["payload_json"])
    assert event["processor_id"] == saved["routing"]["picked_processor_id"]
    impact = client.get("/orgs/org_campus_workshop/dashboard").json()
    assert impact["revenue_inr"]["realised"]["net_inr"] == pytest.approx(saved["receipt"]["diff_rupees"], abs=0.01)
    assert client.put("/streams/sample/route", json={"w": 0}).status_code == 409


def test_handoff_and_pickup_reject_buyer_overrides(runtime):
    _, client, seed = runtime
    seed()
    for buyer in ("nonexistent-buyer", "proc_demo_steel_mill_ludhiana"):
        assert client.post("/streams/sample/handoff", json={"status": "verified", "processor_id": buyer}).status_code == 409
        assert client.post(f"/streams/sample/draft-message?processor_id={buyer}").status_code == 409


def test_reclassification_changes_one_item_and_does_not_approve_it(runtime):
    _, client, seed = runtime
    seed(items=[make_item(confidence=0.4), make_item(material="paper", quantity_kg=20)])
    result = client.post("/streams/sample/review", json={"decision": "reclassify", "reviewer": "Tester",
        "material": "battery_lithium", "item_index": 0})
    assert result.status_code == 200 and result.json()["status"] == "NEEDS_REVIEW"
    stream = client.get("/streams/sample").json()
    first, second = stream["characterization"]["items"]
    assert first["material"] == "battery_lithium" and first["hazardous"]
    assert first["confidence"] == 0.4 and second["material"] == "paper"
    assert [row["stream_id"] for row in client.get("/review-queue").json()] == ["sample"]
    assert client.post("/streams/sample/review", json={"decision": "confirm_routing", "reviewer": "Tester"}).status_code == 409
    assert client.post("/streams/sample/handoff", json={"status": "verified", "processor_id": "proc_demo_foundry_mg"}).status_code == 409


def test_material_hazard_is_enforced_when_model_flag_is_false(runtime):
    _, client, seed = runtime
    seed(items=[make_item(material="battery_lithium", hazardous=False)])
    stream = client.get("/streams/sample").json()
    assert stream["status"] == "NEEDS_REVIEW"
    assert stream["characterization"]["items"][0]["hazardous"]
    assert all(not row["authorization_gate_passed"] for row in stream["routing"][0]["unscored_candidates"])


@pytest.mark.parametrize("old_material,new_material", [
    ("battery_lithium", "paper"), ("battery_lead_acid", "cardboard"),
    ("used_oil", "steel_scrap"), ("e_waste_storage_drive", "steel_scrap"),
])
def test_reclassifying_away_from_material_clears_obsolete_flags(runtime, old_material, new_material):
    storage, client, seed = runtime
    seed(items=[make_item(material=old_material, confidence=0.4), make_item(material="paper")])
    before = client.get("/streams/sample").json()["characterization"]["items"]
    response = client.post("/streams/sample/review", json={"decision": "reclassify", "reviewer": "Tester",
        "material": new_material, "item_index": 0})
    assert response.status_code == 200 and response.json()["status"] == "NEEDS_REVIEW"
    stream = client.get("/streams/sample").json()
    first, second = stream["characterization"]["items"]
    assert first["material"] == new_material
    assert not first["hazardous"] and not first["is_storage_device"]
    assert first["confidence"] == before[0]["confidence"] and second == before[1]
    assert stream["routing"][0]["picked_processor_id"]
    review_event = json.loads(storage.get_ledger_head("sample")["payload_json"])
    assert review_event["previous_classification"]["material"] == old_material
    assert review_event["classification"] == {"material": new_material, "hazardous": False, "is_storage_device": False}
    assert client.post("/streams/sample/review", json={"decision": "confirm_routing", "reviewer": "Tester"}).status_code == 200
    assert client.post("/streams/sample/handoff", json={"status": "matched"}).status_code == 200


@pytest.mark.parametrize("flag", ["hazardous", "is_storage_device"])
def test_reclassification_can_explicitly_retain_independent_safety_flags(runtime, flag):
    _, client, seed = runtime
    seed(items=[make_item(confidence=0.4)])
    response = client.post("/streams/sample/review", json={"decision": "reclassify", "reviewer": "Tester",
        "material": "steel_scrap", flag: True})
    assert response.status_code == 200
    item = client.get("/streams/sample").json()["characterization"]["items"][0]
    assert item[flag]
    confirmation = client.post("/streams/sample/review", json={"decision": "confirm_routing", "reviewer": "Tester"})
    if flag == "hazardous":
        assert confirmation.status_code == 409
    else:
        assert confirmation.status_code == 200
        assert client.post("/streams/sample/handoff", json={"status": "matched"}).status_code == 409


def test_ordinary_characterization_preserves_independent_safety_flags():
    item = make_item(material="paper", hazardous=True, is_storage_device=True)
    assert item.hazardous and item.is_storage_device


def test_out_of_scope_cannot_be_routed_through_preview_or_save(runtime):
    _, client, seed = runtime
    seed(items=[make_item(composition_note="used medical syringes")])
    assert client.get("/streams/sample/route?w=1").json()["routing"]["refused"]
    assert client.put("/streams/sample/route", json={"w": 1}).status_code == 409


def test_multi_item_handoff_has_independent_status_and_measured_weights(runtime):
    storage, client, seed = runtime
    seed(items=[make_item(quantity_kg=10), make_item(material="paper", quantity_kg=20)])
    assert client.post("/streams/sample/handoff", json={"status": "verified", "item_index": 0, "weight_kg": 5}).status_code == 200
    impact = client.get("/orgs/org_campus_workshop/dashboard").json()
    assert impact["kg"]["verified"] == 5
    assert impact["pending"]["awaiting_pickup"] == 1
    assert client.post("/streams/sample/handoff", json={"status": "collected", "item_index": 1, "weight_kg": 12}).status_code == 200
    impact = client.get("/orgs/org_campus_workshop/dashboard").json()
    assert impact["kg"]["collected"] == 17 and impact["kg"]["verified"] == 5
    assert client.post("/streams/sample/handoff", json={"status": "verified", "item_index": 1}).status_code == 200
    assert client.get("/orgs/org_campus_workshop/dashboard").json()["kg"]["verified"] == 17


def test_storage_device_wipe_does_not_unlock_a_different_item(runtime):
    _, client, seed = runtime
    seed(items=[make_item(is_storage_device=True), make_item(is_storage_device=True)])
    assert client.post("/streams/sample/wipe").status_code == 422
    body = {"method": "overwrite", "operator": "Tester", "certificate_ref": "C-1", "item_index": 0}
    assert client.post("/streams/sample/wipe", json=body).status_code == 200
    assert client.post("/streams/sample/handoff", json={"status": "matched", "item_index": 0}).status_code == 200
    assert client.post("/streams/sample/handoff", json={"status": "matched", "item_index": 1}).status_code == 409


def test_verified_handoff_is_final_and_cannot_change_dashboard_credit(runtime):
    storage, client, seed = runtime
    seed()
    assert client.post("/streams/sample/handoff", json={"status": "verified", "weight_kg": 5}).status_code == 200
    links = len(storage.get_ledger_chain("sample"))
    before = client.get("/orgs/org_campus_workshop/dashboard").json()
    for status in ("matched", "collected", "weighed", "verified"):
        response = client.post("/streams/sample/handoff", json={"status": status, "weight_kg": 500})
        assert response.status_code == 409 and "final" in response.json()["detail"]
    after = client.get("/orgs/org_campus_workshop/dashboard").json()
    assert len(storage.get_ledger_chain("sample")) == links
    assert before["kg"]["verified"] == after["kg"]["verified"] == 5
    assert before["revenue_inr"]["realised"] == after["revenue_inr"]["realised"]


def test_handoffs_only_advance_and_different_items_progress_independently(runtime):
    storage, client, seed = runtime
    seed(items=[make_item(), make_item(material="paper")])
    for status in ("matched", "collected", "weighed", "verified"):
        response = client.post("/streams/sample/handoff", json={"status": status, "item_index": 0, "weight_kg": 5})
        assert response.status_code == 200
        links = len(storage.get_ledger_chain("sample"))
        for backwards in ("matched", status):
            assert client.post("/streams/sample/handoff", json={"status": backwards, "weight_kg": 500}).status_code == 409
        assert len(storage.get_ledger_chain("sample")) == links
    assert client.post("/streams/sample/handoff", json={"status": "matched", "item_index": 1}).status_code == 200


def test_dashboard_preserves_first_verification_for_old_repeated_handoffs(runtime):
    storage, client, seed = runtime
    seed()
    # Model a history created by the old unrestricted handoff implementation.
    for status, weight in (("verified", 5), ("matched", 500), ("verified", 500)):
        ledger.append(storage, "sample", f"handoff_{status}", {"item_index": 0, "weight_kg": weight})
    assert ledger.verify(storage, "sample")["ok"]
    assert client.get("/orgs/org_campus_workshop/dashboard").json()["kg"]["verified"] == 5


@pytest.mark.parametrize("key", ["../outside.jpg", "/tmp/outside.jpg", "org_campus_workshop/../../outside.jpg", "..", "photo.jpg/extra"])
def test_photo_paths_cannot_escape_storage(runtime, tmp_path, key):
    storage, client, _ = runtime
    marker = tmp_path / "outside.jpg"
    marker.write_bytes(b"unchanged")
    with pytest.raises(ValueError):
        storage.save_upload(key, JPEG_BYTES)
    with pytest.raises(ValueError):
        storage.read_upload(key)
    with pytest.raises(ValidationError):
        StreamCreateRequest(org_id="org_campus_workshop", photo_keys=[key], pincode="147001")
    assert marker.read_bytes() == b"unchanged"


def test_upload_validation_rejects_invalid_images_counts_and_cross_org_references(runtime):
    _, client, _ = runtime
    for count in (0, -1, 5, 10_000):
        assert client.post("/uploads", json={"org_id": "org_campus_workshop", "count": count}).status_code == 422
    target = client.post("/uploads", json={"org_id": "org_campus_lab", "count": 1}).json()[0]
    assert client.put(target["url"], content=b"not an image").status_code == 422
    assert client.put(target["url"], content=JPEG_BYTES).status_code == 200
    assert client.post("/streams", json={"org_id": "org_campus_workshop", "pincode": "147001", "photo_keys": [target["key"]]}).status_code == 403
    assert client.post("/streams", json={"org_id": "org_campus_workshop", "pincode": "147001", "photo_keys": ["org_campus_workshop/missing.jpg"]}).status_code == 422
    assert client.post("/streams", json={"org_id": "org_campus_workshop", "pincode": "147001", "photo_keys": []}).status_code == 422
    assert client.put(target["url"], content=b"x" * (5 * 1024 * 1024 + 1)).status_code == 413


def test_uploaded_passport_photo_cannot_be_replaced(runtime, monkeypatch):
    storage, client, _ = runtime
    target = client.post("/uploads", json={"org_id": "org_campus_workshop", "count": 1}).json()[0]
    assert client.put(target["url"], content=JPEG_BYTES).status_code == 200
    monkeypatch.setattr(pipeline, "characterize_waste", lambda *args, **kwargs:
        Characterization(items=[make_item()], overall_confidence=0.9))
    created = client.post("/streams", json={"org_id": "org_campus_workshop", "pincode": "147001", "photo_keys": [target["key"]]})
    assert created.status_code == 202
    sid = created.json()["stream_id"]
    assert client.get(f"/streams/{sid}").json()["status"] == "ROUTED"
    replacement = BytesIO()
    Image.new("RGB", (4, 4), "red").save(replacement, format="JPEG")
    for data in (JPEG_BYTES, replacement.getvalue()):
        response = client.put(target["url"], content=data)
        assert response.status_code == 409 and "already uploaded" in response.json()["detail"]
    assert client.get(target["url"]).content == storage.read_upload(target["key"]) == JPEG_BYTES
    assert client.get(f"/streams/{sid}").json()["photo_keys"] == [target["key"]]


@pytest.mark.parametrize("quantity", [0, -1, float("nan"), float("inf")])
def test_weights_are_positive_and_finite(quantity):
    with pytest.raises(ValidationError):
        make_item(quantity_kg=quantity)
    with pytest.raises(ValidationError):
        StreamCreateRequest(org_id="org_campus_workshop", photo_keys=["photo.jpg"], quantity_kg=quantity)


@pytest.mark.parametrize("confidence", [-0.1, 1.1, float("nan"), float("inf")])
def test_model_confidence_is_bounded(confidence):
    with pytest.raises(ValidationError):
        make_item(confidence=confidence)


def test_cache_includes_weight_note_models_and_image_boundaries(runtime, monkeypatch):
    storage, _, _ = runtime
    calls = []
    def model(tier, prompt):
        calls.append(prompt[0]["text"])
        return Characterization(items=[make_item()], overall_confidence=0.9)
    monkeypatch.setattr(characterize, "_run_model", model)
    photos = [{"format": "jpeg", "bytes": JPEG_BYTES}]
    characterize.characterize_waste(photos, "clean", 10, storage)
    characterize.characterize_waste(photos, "clean", 10, storage)
    characterize.characterize_waste(photos, "clean", 250, storage)
    characterize.characterize_waste(photos, "oil stains", 250, storage)
    assert len(calls) == 3
    original = characterize.compute_image_hash(photos)
    monkeypatch.setenv("MODEL_FAST", "different-model")
    get_settings.cache_clear()
    assert characterize.compute_image_hash(photos) != original
    assert characterize.compute_image_hash([{"format": "jpeg", "bytes": b"a"}, {"format": "jpeg", "bytes": b"bc"}]) != \
        characterize.compute_image_hash([{"format": "jpeg", "bytes": b"ab"}, {"format": "jpeg", "bytes": b"c"}])


def test_strong_tier_is_never_retried_twice(runtime, monkeypatch):
    storage, _, _ = runtime
    calls = []
    def model(tier, prompt):
        calls.append(tier)
        if tier == "strong":
            raise MaxTokensReachedException("test budget exhausted")
        return Characterization(items=[make_item(confidence=0.4)], overall_confidence=0.4)
    monkeypatch.setattr(characterize, "_run_model", model)
    with pytest.raises(MaxTokensReachedException):
        characterize.characterize_waste([{"format": "jpeg", "bytes": JPEG_BYTES}], storage=storage)
    assert calls == ["fast", "strong"]


def test_pdf_download_is_parseable_and_contains_all_items_and_provenance(runtime):
    _, client, seed = runtime
    seed(items=[make_item(quantity_kg=10), make_item(material="paper", quantity_kg=20)])
    response = client.get("/streams/sample/report")
    assert response.status_code == 200 and response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    reader = PdfReader(BytesIO(response.content))
    text = "\n".join(page.extract_text() for page in reader.pages)
    for expected in ("LoopBack Waste Passport", "Item 1: steel scrap", "Item 2: paper", "Demo data", "Ledger:", "Emission factor:"):
        assert expected in text
    assert client.get("/streams/sample/report?format=json").json()["stream_id"] == "sample"


def test_scoped_administrator_cannot_tamper_another_organization(runtime, monkeypatch):
    _, client, seed = runtime
    seed("lab", org_id="org_campus_lab")
    monkeypatch.setenv("API_TOKENS_JSON", json.dumps([{ "token": "test-administrator-credential-only",
        "subject": "Scoped admin", "role": "admin", "org_ids": ["org_campus_workshop"] }]))
    assert client.post("/dev/tamper/lab").status_code == 403


def test_missing_weight_is_explicit_and_measured_handoff_can_receive_credit(runtime):
    _, client, seed = runtime
    seed(items=[make_item(quantity_kg=None)])
    receipt = client.get("/streams/sample").json()["receipts"][0]
    assert receipt["quantity_kg"] is None and receipt["warning"]
    assert receipt["diff_rupees"] is None and receipt["diff_co2e_kg"] is None
    assert client.post("/streams/sample/handoff", json={"status": "verified", "weight_kg": 10}).status_code == 200
    impact = client.get("/orgs/org_campus_workshop/dashboard").json()
    assert impact["kg"]["verified"] == 10
    assert impact["revenue_inr"]["realised"]["net_inr"] > 0


def test_e_waste_inputs_are_bounded_and_wipes_record_authenticated_actor(runtime):
    storage, client, seed = runtime
    seed()
    for device in ({"asset_tag": "A", "storage_drives": 1_000_000},
                   {"asset_tag": "A", "storage_drives": 1.5}, {"asset_tag": "A", "weight_kg": -1}):
        assert client.post("/streams/sample/ewaste", json={"devices": [device]}).status_code == 422
    assert client.post("/streams/sample/ewaste", json={"devices": [{"asset_tag": "A", "storage_drives": 1}]}).status_code == 200
    operator = TestClient(main.app, headers={"Authorization": "Bearer test-workshop-operator-credential"})
    record = {"method": "overwrite", "certificate_ref": "C-1", "operator": "Named technician"}
    assert operator.post("/streams/sample/ewaste/drives/A-D1/wipe", json=record).status_code == 403
    assert client.post("/streams/sample/ewaste/drives/A-D1/wipe", json=record).status_code == 200
    assert json.loads(storage.get_ledger_head("sample")["payload_json"])["actor"] == "Test admin"


def test_reuse_choice_does_not_credit_an_unused_recycler():
    item = make_item(material="e_waste_computer", composition_note="working laptop", quantity_kg=10)
    routing = {"reuse_recommended_processor_id": "reuse", "picked_processor_id": "recycler",
        "candidates": [{"processor_id": "recycler", "name": "Unused recycler", "tier": "recycle",
                        "net_rupees": 999, "net_co2e_kg": 999}], "review_required": False}
    assert report.counterfactual_receipt(item, routing).diff_rupees is None
    assert report.dashboard_summary([(item, routing)])["kg_by_tier"]["reuse"] == 10
    impact = report.org_impact([{"stream_id": "reuse", "status": "ROUTED",
        "characterization": {"items": [item.model_dump()]}, "routing": [routing]}], {})
    assert impact["kg_by_tier"]["reuse"] == 10
    assert impact["kg_by_tier"]["recycle"] == 0
    assert impact["revenue_inr"]["projected"]["net_inr"] == 0


def test_legacy_schema_is_preserved_and_never_rehashed(tmp_path):
    import sqlite3
    from app.storage.local import LocalStorage
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE ledger (chain_id TEXT, link_no INTEGER, event TEXT, payload_json TEXT, "
                 "prev_hash TEXT, entry_hash TEXT, ts TEXT, PRIMARY KEY(chain_id, link_no))")
    conn.execute("INSERT INTO ledger VALUES ('legacy', 1, 'requested', '{}', ?, 'original-hash', 'original-time')", (ledger.GENESIS,))
    conn.commit(); conn.close()
    storage = LocalStorage(path)
    entry = storage.get_ledger_head("legacy")
    assert entry["hash_version"] == 1 and entry["entry_hash"] == "original-hash"
    assert not ledger.verify(storage, "legacy")["ok"]
    with pytest.raises(PermissionError):
        ledger.append(storage, "legacy", "data_wipe_confirmed", {})
    assert storage.get_ledger_head("legacy")["entry_hash"] == "original-hash"
