import tempfile
from pathlib import Path

import pytest

from app.models import Item
from app.storage.local import LocalStorage
from app.tools import ledger


@pytest.fixture
def storage():
    with tempfile.TemporaryDirectory() as tmp:
        yield LocalStorage(db_path=Path(tmp) / "test.db")


def make_item(**overrides) -> Item:
    defaults = dict(
        material="e_waste_storage_drive", composition_note="HDD", quantity_kg=0.5,
        quantity_basis="estimated", purity="high", hazardous=False,
        is_storage_device=True, confidence=0.9, reasoning="drive",
    )
    defaults.update(overrides)
    return Item(**defaults)


def test_first_entry_uses_genesis_prev_hash(storage):
    entry = ledger.append(storage, "chain1", "requested", {"a": 1})
    assert entry["link_no"] == 1
    assert entry["prev_hash"] == ledger.GENESIS


def test_entries_chain_together(storage):
    e1 = ledger.append(storage, "chain1", "requested", {"a": 1})
    e2 = ledger.append(storage, "chain1", "matched", {"b": 2})
    assert e2["link_no"] == 2
    assert e2["prev_hash"] == e1["entry_hash"]


def test_verify_passes_on_a_clean_chain(storage):
    ledger.append(storage, "chain1", "requested", {"a": 1})
    ledger.append(storage, "chain1", "matched", {"b": 2})
    ledger.append(storage, "chain1", "collected", {"c": 3})

    result = ledger.verify(storage, "chain1")
    assert result == {"ok": True, "links": 3, "first_broken": None}


def test_verify_on_empty_chain_is_ok(storage):
    assert ledger.verify(storage, "nonexistent") == {"ok": True, "links": 0, "first_broken": None}


def test_verify_fails_after_tampering_payload(storage):
    ledger.append(storage, "chain1", "requested", {"a": 1})
    ledger.append(storage, "chain1", "matched", {"b": 2})
    ledger.append(storage, "chain1", "collected", {"c": 3})

    # Directly tamper the stored payload_json of link 2, simulating editing a row in the DB console.
    storage._conn.execute(
        "UPDATE ledger SET payload_json = ? WHERE chain_id = ? AND link_no = 2",
        ('{"b":999}', "chain1"),
    )
    storage._conn.commit()

    result = ledger.verify(storage, "chain1")
    assert result["ok"] is False
    assert result["first_broken"] == 2


def test_canonical_json_is_byte_identical_regardless_of_key_order():
    a = ledger.canonical({"b": 2, "a": 1})
    b = ledger.canonical({"a": 1, "b": 2})
    assert a == b


def test_storage_device_cannot_be_matched_without_wipe(storage):
    drive = make_item()
    ledger.record_handoff(storage, "stream1", "proc1", "requested", drive)
    with pytest.raises(PermissionError):
        ledger.record_handoff(storage, "stream1", "proc1", "matched", drive)


def test_storage_device_can_be_matched_after_wipe_confirmed(storage):
    drive = make_item()
    ledger.record_handoff(storage, "stream1", "proc1", "requested", drive)
    ledger.record_wipe_confirmed(storage, "stream1")
    entry = ledger.record_handoff(storage, "stream1", "proc1", "matched", drive)
    assert entry["event"] == "handoff_matched"


def test_non_storage_device_moves_freely(storage):
    scrap = make_item(material="steel_scrap", is_storage_device=False)
    ledger.record_handoff(storage, "stream2", "proc1", "requested", scrap)
    entry = ledger.record_handoff(storage, "stream2", "proc1", "matched", scrap)
    assert entry["event"] == "handoff_matched"
