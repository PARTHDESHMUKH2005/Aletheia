import tempfile
from pathlib import Path

import pytest

from app.storage.local import LocalStorage


@pytest.fixture
def storage():
    with tempfile.TemporaryDirectory() as tmp:
        yield LocalStorage(db_path=Path(tmp) / "test.db")


def test_create_and_get_stream(storage):
    storage.create_stream("s1", {"status": "SUBMITTED", "org_id": "org1"})
    assert storage.get_stream("s1") == {"status": "SUBMITTED", "org_id": "org1"}


def test_get_missing_stream_returns_none(storage):
    assert storage.get_stream("does-not-exist") is None


def test_update_stream_merges_fields(storage):
    storage.create_stream("s1", {"status": "SUBMITTED"})
    storage.update_stream("s1", status="ROUTED", confidence=0.9)
    assert storage.get_stream("s1") == {"status": "ROUTED", "confidence": 0.9}


def test_update_missing_stream_raises(storage):
    with pytest.raises(KeyError):
        storage.update_stream("missing", status="ROUTED")


def test_cache_roundtrip(storage):
    assert storage.get_cached_characterization("sha123") is None
    storage.set_cached_characterization("sha123", {"items": [], "overall_confidence": 0.5})
    assert storage.get_cached_characterization("sha123") == {"items": [], "overall_confidence": 0.5}
