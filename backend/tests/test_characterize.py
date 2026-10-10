from app.models import Characterization, Item
from app.tools import characterize


class FakeStorage:
    def __init__(self):
        self.cache: dict[str, dict] = {}

    def get_cached_characterization(self, image_sha):
        return self.cache.get(image_sha)

    def set_cached_characterization(self, image_sha, characterization):
        self.cache[image_sha] = characterization


def make_characterization(confidence: float) -> Characterization:
    return Characterization(
        items=[Item(
            material="steel_scrap", composition_note="can", quantity_kg=0.3,
            quantity_basis="estimated", purity="high", hazardous=False,
            is_storage_device=False, confidence=confidence, reasoning="stub",
        )],
        overall_confidence=confidence,
    )


def test_high_confidence_does_not_escalate(monkeypatch):
    calls = []

    def fake_run_model(tier, prompt):
        calls.append(tier)
        return make_characterization(0.9)

    monkeypatch.setattr(characterize, "_run_model", fake_run_model)

    result = characterize.characterize_waste(
        photos=[{"format": "jpeg", "bytes": b"photo-high-confidence"}],
        storage=FakeStorage(),
    )
    assert calls == ["fast"]
    assert result.overall_confidence == 0.9


def test_low_confidence_escalates_once_and_never_loops(monkeypatch):
    calls = []

    def fake_run_model(tier, prompt):
        calls.append(tier)
        # Both fast and strong return low confidence -- must still stop after one escalation.
        return make_characterization(0.4)

    monkeypatch.setattr(characterize, "_run_model", fake_run_model)

    result = characterize.characterize_waste(
        photos=[{"format": "jpeg", "bytes": b"photo-low-confidence"}],
        storage=FakeStorage(),
    )
    assert calls == ["fast", "strong"]
    assert result.overall_confidence == 0.4


def test_escalation_recovers_confidence(monkeypatch):
    responses = iter([make_characterization(0.5), make_characterization(0.95)])

    def fake_run_model(tier, prompt):
        return next(responses)

    monkeypatch.setattr(characterize, "_run_model", fake_run_model)

    result = characterize.characterize_waste(
        photos=[{"format": "jpeg", "bytes": b"photo-recovers"}],
        storage=FakeStorage(),
    )
    assert result.overall_confidence == 0.95


def test_cache_hit_skips_the_model_entirely(monkeypatch):
    def fail_if_called(tier, prompt):
        raise AssertionError("model should not be called on a cache hit")

    monkeypatch.setattr(characterize, "_run_model", fail_if_called)

    photos = [{"format": "jpeg", "bytes": b"photo-cached"}]
    image_hash = characterize.compute_image_hash(photos)
    storage = FakeStorage()
    storage.set_cached_characterization(image_hash, make_characterization(0.9).model_dump())

    result = characterize.characterize_waste(photos=photos, storage=storage)
    assert result.overall_confidence == 0.9


def test_image_hash_is_order_sensitive_and_stable():
    a = [{"format": "jpeg", "bytes": b"one"}, {"format": "jpeg", "bytes": b"two"}]
    b = [{"format": "jpeg", "bytes": b"two"}, {"format": "jpeg", "bytes": b"one"}]
    assert characterize.compute_image_hash(a) != characterize.compute_image_hash(b)
    assert characterize.compute_image_hash(a) == characterize.compute_image_hash(a)


def test_more_than_max_photos_is_truncated(monkeypatch):
    seen_prompts = []

    def fake_run_model(tier, prompt):
        seen_prompts.append(prompt)
        return make_characterization(0.9)

    monkeypatch.setattr(characterize, "_run_model", fake_run_model)

    photos = [{"format": "jpeg", "bytes": f"p{i}".encode()} for i in range(6)]
    characterize.characterize_waste(photos=photos, storage=FakeStorage())

    image_blocks = [b for b in seen_prompts[0] if "image" in b]
    assert len(image_blocks) == characterize.MAX_PHOTOS
