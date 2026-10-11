import tempfile
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
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


def test_concurrent_photo_uploads_publish_one_complete_file(storage):
    barrier = Barrier(2)
    versions = (b"a" * 100_000, b"b" * 100_000)

    def upload(data):
        barrier.wait(timeout=10)
        try:
            storage.save_upload("org/photo.jpg", data)
            return data
        except FileExistsError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(upload, data) for data in versions]
        outcomes = [future.result(timeout=15) for future in futures]
    winners = [outcome for outcome in outcomes if outcome is not None]
    assert len(winners) == 1
    assert storage.read_upload("org/photo.jpg") == winners[0]
    assert not list(storage.uploads_dir.rglob(".upload-*"))
