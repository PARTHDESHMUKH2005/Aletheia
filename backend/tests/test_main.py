import pytest
from fastapi.testclient import TestClient

from app import pipeline
from app.main import app
from app.models import Characterization, Item

client = TestClient(app)


def make_characterization(material="steel_scrap", confidence=0.9, quantity_kg=100.0) -> Characterization:
    return Characterization(
        items=[Item(
            material=material, composition_note="clean steel can", quantity_kg=quantity_kg,
            quantity_basis="estimated", purity="high", hazardous=False,
            is_storage_device=False, confidence=confidence, reasoning="stub",
        )],
        overall_confidence=confidence,
    )


@pytest.fixture(autouse=True)
def stub_characterize(monkeypatch):
    monkeypatch.setattr(pipeline, "characterize_waste", lambda *a, **k: make_characterization())


def create_routed_stream() -> str:
    upload = client.post("/uploads", json={"count": 1}).json()[0]
    put_resp = client.put(upload["url"], content=b"fake-jpeg-bytes")
    assert put_resp.status_code == 200

    create_resp = client.post("/streams", json={
        "org_id": "org_campus_workshop", "note": "test", "photo_keys": [upload["key"]], "pincode": "147001",
    })
    assert create_resp.status_code == 202
    return create_resp.json()["stream_id"]


def test_uploads_returns_matching_key_and_url():
    targets = client.post("/uploads", json={"count": 2}).json()
    assert len(targets) == 2
    for t in targets:
        assert t["key"] in t["url"]


def test_create_stream_unknown_org_is_404():
    resp = client.post("/streams", json={"org_id": "does-not-exist", "photo_keys": ["x.jpg"]})
    assert resp.status_code == 404


def test_full_flow_stream_reaches_routed():
    stream_id = create_routed_stream()
    resp = client.get(f"/streams/{stream_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ROUTED"
    assert body["characterization"]["items"][0]["material"] == "steel_scrap"
    assert isinstance(body["ledger"], list)
    assert len(body["ledger"]) >= 1


def test_get_stream_404_for_missing_stream():
    resp = client.get("/streams/does-not-exist")
    assert resp.status_code == 404


def test_route_endpoint_returns_ranked_candidates_and_receipt():
    stream_id = create_routed_stream()
    resp = client.get(f"/streams/{stream_id}/route", params={"w": 0.0})
    assert resp.status_code == 200
    body = resp.json()
    assert body["routing"]["picked_processor_id"] is not None
    assert "receipt" in body
    assert body["receipt"]["material"] == "steel_scrap"


def test_route_endpoint_consistent_receipt_arithmetic():
    stream_id = create_routed_stream()
    body = client.get(f"/streams/{stream_id}/route", params={"w": 0.5}).json()
    receipt = body["receipt"]
    assert receipt["diff_rupees"] == receipt["chosen_case"]["value_inr"] - receipt["default_case"]["value_inr"]
    assert receipt["diff_co2e_kg"] == receipt["chosen_case"]["co2e_kg"] - receipt["default_case"]["co2e_kg"]


def test_route_endpoint_rejects_out_of_range_w():
    stream_id = create_routed_stream()
    resp = client.get(f"/streams/{stream_id}/route", params={"w": 1.5})
    assert resp.status_code == 422


def test_route_endpoint_404_before_characterization():
    upload = client.post("/uploads", json={"count": 1}).json()[0]
    client.put(upload["url"], content=b"fake")
    # Don't call POST /streams (which triggers the background pipeline) -- hit
    # /route on a nonexistent stream id directly instead.
    resp = client.get("/streams/not-a-real-stream/route")
    assert resp.status_code == 404


def test_wipe_confirmation_is_recorded_in_ledger():
    stream_id = create_routed_stream()
    resp = client.post(f"/streams/{stream_id}/wipe")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    ledger_entries = client.get(f"/streams/{stream_id}").json()["ledger"]
    assert any(e["event"] == "data_wipe_confirmed" for e in ledger_entries)


def test_draft_message_is_never_sent_and_is_recorded(monkeypatch):
    stream_id = create_routed_stream()
    route = client.get(f"/streams/{stream_id}/route", params={"w": 0.5}).json()
    processor_id = route["routing"]["picked_processor_id"]

    # Fail the test if any outbound HTTP call is attempted from inside the draft-message endpoint.
    import httpx
    def fail_if_outbound(*a, **k):
        raise AssertionError("draft-message endpoint must never make an outbound call")
    monkeypatch.setattr(httpx.Client, "send", fail_if_outbound)

    resp = client.post(f"/streams/{stream_id}/draft-message", params={"processor_id": processor_id})
    assert resp.status_code == 200
    body = resp.json()
    assert body["sent"] is False
    assert "Not sent" in body["label"]
    assert body["draft_message"]

    ledger_entries = client.get(f"/streams/{stream_id}").json()["ledger"]
    assert any(e["event"] == "pickup_requested" for e in ledger_entries)


def test_processors_endpoint_lists_seeded_processors():
    resp = client.get("/processors")
    assert resp.status_code == 200
    processors = resp.json()
    assert len(processors) > 0
    assert all(p["seeded"] is True for p in processors)


def test_verify_endpoint_ok_on_clean_chain():
    stream_id = create_routed_stream()
    resp = client.get(f"/verify/{stream_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["first_broken"] is None


def test_verify_endpoint_red_after_tamper():
    stream_id = create_routed_stream()
    from app.config import get_storage
    storage = get_storage()
    storage._conn.execute(
        "UPDATE ledger SET payload_json = ? WHERE chain_id = ? AND link_no = 1",
        ('{"tampered":true}', stream_id),
    )
    storage._conn.commit()

    resp = client.get(f"/verify/{stream_id}")
    body = resp.json()
    assert body["ok"] is False
    assert body["first_broken"] == 1


def test_dashboard_for_unknown_org_is_404():
    resp = client.get("/orgs/does-not-exist/dashboard")
    assert resp.status_code == 404


def test_dashboard_includes_disclaimer():
    resp = client.get("/orgs/org_campus_workshop/dashboard")
    assert resp.status_code == 200
    assert "Routing aid only" in resp.json()["disclaimer"]


def test_dev_tamper_endpoint_turns_verify_red():
    stream_id = create_routed_stream()
    assert client.get(f"/verify/{stream_id}").json()["ok"] is True

    resp = client.post(f"/dev/tamper/{stream_id}", params={"link_no": 1})
    assert resp.status_code == 200
    assert resp.json()["tampered"] is True

    verify = client.get(f"/verify/{stream_id}").json()
    assert verify["ok"] is False
    assert verify["first_broken"] == 1


def test_dev_tamper_endpoint_disabled_in_production(monkeypatch):
    from app import main as main_module
    monkeypatch.setenv("ENV", "production")
    main_module.get_settings.cache_clear()
    try:
        stream_id = create_routed_stream()
        resp = client.post(f"/dev/tamper/{stream_id}", params={"link_no": 1})
        assert resp.status_code == 403
    finally:
        monkeypatch.delenv("ENV", raising=False)
        main_module.get_settings.cache_clear()


def test_dev_tamper_endpoint_404_for_missing_link():
    stream_id = create_routed_stream()
    resp = client.post(f"/dev/tamper/{stream_id}", params={"link_no": 999})
    assert resp.status_code == 404
