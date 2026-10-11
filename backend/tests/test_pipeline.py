import tempfile
from pathlib import Path

import pytest

from app import pipeline
from app.models import Characterization, Item
from app.storage.local import LocalStorage


@pytest.fixture
def storage():
    with tempfile.TemporaryDirectory() as tmp:
        store = LocalStorage(db_path=Path(tmp) / "test.db")
        try:
            yield store
        finally:
            store.close()


def make_characterization(material="steel_scrap", confidence=0.9, hazardous=False, note="clean steel can", quantity_kg=100.0) -> Characterization:
    return Characterization(
        items=[Item(
            material=material, composition_note=note, quantity_kg=quantity_kg,
            quantity_basis="estimated", purity="high", hazardous=hazardous,
            is_storage_device=False, confidence=confidence, reasoning="stub",
        )],
        overall_confidence=confidence,
    )


def seed_stream(storage, stream_id="s1", org_id="org_campus_workshop", **extra):
    storage.save_upload("photo1.jpg", b"fake-bytes")
    data = {
        "org_id": org_id, "note": "", "quantity_kg": None,
        "photo_keys": ["photo1.jpg"], "pincode": "147001", "slider_w": 0.5, "status": "SUBMITTED",
    }
    data.update(extra)
    storage.create_stream(stream_id, data)


def test_pipeline_is_idempotent_for_non_submitted_streams(storage, monkeypatch):
    def fail_if_called(*a, **k):
        raise AssertionError("characterize_waste should not be called")
    monkeypatch.setattr(pipeline, "characterize_waste", fail_if_called)

    seed_stream(storage, status="ROUTED")
    result = pipeline.run_pipeline("s1", storage=storage)
    assert result["status"] == "ROUTED"


def test_pipeline_happy_path_routes_steel_scrap(storage, monkeypatch):
    monkeypatch.setattr(pipeline, "characterize_waste", lambda *a, **k: make_characterization())
    seed_stream(storage)

    result = pipeline.run_pipeline("s1", storage=storage)
    assert result["status"] == "ROUTED"
    assert result["routing"][0]["picked_processor_id"] is not None
    assert "characterize_ms" in result["timings"]


def test_pipeline_low_confidence_needs_review(storage, monkeypatch):
    monkeypatch.setattr(pipeline, "characterize_waste", lambda *a, **k: make_characterization(confidence=0.5))
    seed_stream(storage)

    result = pipeline.run_pipeline("s1", storage=storage)
    assert result["status"] == "NEEDS_REVIEW"


def test_pipeline_hazardous_item_always_needs_review(storage, monkeypatch):
    monkeypatch.setattr(
        pipeline, "characterize_waste",
        lambda *a, **k: make_characterization(material="used_oil", hazardous=True, confidence=0.9, note="jerry can of used motor oil"),
    )
    seed_stream(storage)

    result = pipeline.run_pipeline("s1", storage=storage)
    assert result["status"] == "NEEDS_REVIEW"


def test_pipeline_out_of_scope_item_is_refused(storage, monkeypatch):
    monkeypatch.setattr(
        pipeline, "characterize_waste",
        lambda *a, **k: make_characterization(material="other", note="box of used syringes and needles"),
    )
    seed_stream(storage)

    result = pipeline.run_pipeline("s1", storage=storage)
    assert result["status"] == "NEEDS_REVIEW"
    assert result["routing"][0]["refused"] is True
    assert result["routing"][0]["out_of_scope_category"] == "bio_medical"


def test_pipeline_writes_a_ledger_entry_for_the_pick(storage, monkeypatch):
    monkeypatch.setattr(pipeline, "characterize_waste", lambda *a, **k: make_characterization())
    seed_stream(storage)

    pipeline.run_pipeline("s1", storage=storage)
    chain = storage.get_ledger_chain("s1")
    assert any(e["event"] == "handoff_requested" for e in chain)


def test_pipeline_missing_stream_raises(storage):
    with pytest.raises(KeyError):
        pipeline.run_pipeline("does-not-exist", storage=storage)
