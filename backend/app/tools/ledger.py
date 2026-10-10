"""record_handoff tool plus canonical/compute_hash/append/verify for the
hash-chained ledger (BUILD.md section 6). One chain per stream: chain_id = stream_id.

append() goes through the Storage interface (append_ledger_entry does the
conditional/unique-constraint insert) so the same code runs against SQLite
locally and DynamoDB on AWS -- only storage/aws.py changes in Phase 3.
"""
import hashlib
import json
from datetime import datetime, timezone

GENESIS = "0" * 64


def canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_hash(prev_hash: str, payload_json: str, ts: str) -> str:
    return hashlib.sha256((prev_hash + payload_json + ts).encode("utf-8")).hexdigest()


def append(storage, chain_id: str, event: str, payload: dict, retries: int = 3) -> dict:
    for _ in range(retries):
        head = storage.get_ledger_head(chain_id)
        link_no = head["link_no"] + 1 if head else 1
        prev_hash = head["entry_hash"] if head else GENESIS
        ts = datetime.now(timezone.utc).isoformat()
        payload_json = canonical(payload)
        entry = {
            "chain_id": chain_id,
            "link_no": link_no,
            "event": event,
            "payload_json": payload_json,
            "prev_hash": prev_hash,
            "ts": ts,
            "entry_hash": compute_hash(prev_hash, payload_json, ts),
        }
        if storage.append_ledger_entry(entry):
            return entry
    raise RuntimeError("ledger append kept colliding")


def verify(storage, chain_id: str) -> dict:
    """Walks the chain from link 1, recomputes every hash, checks each prev_hash
    against the previous entry. Returns {ok, links, first_broken}.
    """
    chain = storage.get_ledger_chain(chain_id)
    expected_prev = GENESIS
    for i, entry in enumerate(chain, start=1):
        if entry["link_no"] != i:
            return {"ok": False, "links": len(chain), "first_broken": i}
        if entry["prev_hash"] != expected_prev:
            return {"ok": False, "links": len(chain), "first_broken": i}
        recomputed = compute_hash(entry["prev_hash"], entry["payload_json"], entry["ts"])
        if recomputed != entry["entry_hash"]:
            return {"ok": False, "links": len(chain), "first_broken": i}
        expected_prev = entry["entry_hash"]
    return {"ok": True, "links": len(chain), "first_broken": None}


def get_ledger_events(storage, chain_id: str) -> list[str]:
    """Event names in order -- what guardrails.can_advance_storage_device needs."""
    return [entry["event"] for entry in storage.get_ledger_chain(chain_id)]


# --- record_handoff: the handoff state machine (status values in BUILD.md section 2) ---

def record_handoff(storage, stream_id: str, processor_id: str, status: str, item, payload: dict | None = None) -> dict:
    """Appends a ledger entry for this handoff status. Refuses to move a storage
    device past 'requested' until the chain holds a data_wipe_confirmed event
    (guardrail 4) -- LoopBack policy, not a legal requirement.
    """
    from app.tools import guardrails

    if status != "requested":
        existing_events = get_ledger_events(storage, stream_id)
        if not guardrails.can_advance_storage_device(item, existing_events):
            raise PermissionError(
                f"{guardrails.STORAGE_DEVICE_POLICY_NOTE} stream_id={stream_id} is blocked at 'requested'."
            )

    event_payload = {"processor_id": processor_id, "status": status, **(payload or {})}
    return append(storage, stream_id, event=f"handoff_{status}", payload=event_payload)


def record_wipe_confirmed(storage, stream_id: str, payload: dict | None = None) -> dict:
    """Records the data_wipe_confirmed event that unblocks a storage device."""
    return append(storage, stream_id, event="data_wipe_confirmed", payload=payload or {})
