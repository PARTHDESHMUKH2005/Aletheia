"""record_handoff tool plus canonical/compute_hash/append/verify for the
hash-chained ledger (BUILD.md section 6). One chain per stream: chain_id = stream_id.

append() goes through the Storage interface (append_ledger_entry does the
conditional/unique-constraint insert) so the same code runs against SQLite
locally and DynamoDB on AWS.
"""
import hashlib
import json
from datetime import datetime, timezone

GENESIS = "0" * 64
HANDOFF_ORDER = ("requested", "matched", "collected", "weighed", "verified")


def canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def compute_hash(prev_hash: str, payload_json: str, ts: str, *, chain_id: str, link_no: int, event: str) -> str:
    envelope = {"hash_version": 2, "chain_id": chain_id, "link_no": link_no,
                "event": event, "prev_hash": prev_hash, "payload_json": payload_json, "ts": ts}
    return hashlib.sha256(canonical(envelope).encode("utf-8")).hexdigest()


def append(storage, chain_id: str, event: str, payload: dict, retries: int = 3, *, guard=None) -> dict:
    """Validate and extend the same chain snapshot, rechecking guards on collisions."""
    for _ in range(retries):
        chain = storage.get_ledger_chain(chain_id)
        if chain and not _verify_chain(chain, chain_id)["ok"]:
            raise PermissionError("ledger is damaged or uses the legacy hash format")
        if guard:
            guard(chain)
        head = chain[-1] if chain else None
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
            "hash_version": 2,
            "entry_hash": compute_hash(prev_hash, payload_json, ts, chain_id=chain_id, link_no=link_no, event=event),
        }
        if storage.append_ledger_entry(entry):
            return entry
    raise RuntimeError("ledger append kept colliding")


def verify(storage, chain_id: str) -> dict:
    """Walks the chain from link 1, recomputes every hash, checks each prev_hash
    against the previous entry. Returns {ok, links, first_broken}.
    """
    return _verify_chain(storage.get_ledger_chain(chain_id), chain_id)


def _verify_chain(chain: list[dict], chain_id: str) -> dict:
    if not chain:
        return {"ok": False, "links": 0, "first_broken": None}
    expected_prev = GENESIS
    for i, entry in enumerate(chain, start=1):
        if entry.get("hash_version") != 2 or entry["chain_id"] != chain_id or entry["link_no"] != i:
            return {"ok": False, "links": len(chain), "first_broken": i}
        if entry["prev_hash"] != expected_prev:
            return {"ok": False, "links": len(chain), "first_broken": i}
        recomputed = compute_hash(entry["prev_hash"], entry["payload_json"], entry["ts"],
            chain_id=entry["chain_id"], link_no=entry["link_no"], event=entry["event"])
        if recomputed != entry["entry_hash"]:
            return {"ok": False, "links": len(chain), "first_broken": i}
        expected_prev = entry["entry_hash"]
    return {"ok": True, "links": len(chain), "first_broken": None}


def get_ledger_events(storage, chain_id: str, item_index: int = 0) -> list[str]:
    """Event names in order -- what guardrails.can_advance_storage_device needs."""
    return [entry["event"] for entry in storage.get_ledger_chain(chain_id)
            if json.loads(entry["payload_json"]).get("item_index", 0) == item_index]


def item_events(events: list[dict], item_index: int, item_count: int) -> list[dict]:
    """Legacy entries without item identity apply only to a single-item stream."""
    return [entry for entry in events if
        json.loads(entry["payload_json"]).get("item_index", 0 if item_count == 1 else None) == item_index]


# --- record_handoff: the handoff state machine (status values in BUILD.md section 2) ---

def record_handoff(storage, stream_id: str, processor_id: str, status: str, item, payload: dict | None = None,
                   *, item_index: int = 0) -> dict:
    """Advance an item's handoff strictly forward; verified is final.

    Forward jumps are allowed, with missing paperwork reported separately. Storage
    devices need a wipe before leaving 'requested' (LoopBack policy).
    """
    from app.tools import guardrails
    from app.tools.ewaste import blocking_reasons

    if status not in HANDOFF_ORDER:
        raise ValueError("invalid handoff status")
    target = HANDOFF_ORDER.index(status)

    def validate_transition(chain):
        stream = storage.get_stream(stream_id) or {}
        item_count = len((stream.get("characterization") or {}).get("items") or [item])
        scoped = item_events(chain, item_index, item_count)
        existing_events = [entry["event"] for entry in scoped]
        reached = [HANDOFF_ORDER.index(event.removeprefix("handoff_")) for event in existing_events
                   if event.removeprefix("handoff_") in HANDOFF_ORDER and event.startswith("handoff_")]
        current = max(reached, default=-1)
        if target <= current:
            if HANDOFF_ORDER[current] == "verified":
                raise PermissionError("verified handoff is final")
            raise PermissionError(f"handoff can only advance; item is already {HANDOFF_ORDER[current]}")
        if status == "requested":
            return
        batch = stream.get("ewaste")
        if batch and batch.get("drives") and not blocking_reasons(batch):
            existing_events.append("data_wipe_confirmed")
        if not guardrails.can_advance_storage_device(item, existing_events):
            raise PermissionError(
                f"{guardrails.STORAGE_DEVICE_POLICY_NOTE} stream_id={stream_id} is blocked at 'requested'."
            )

    event_payload = {**(payload or {}), "processor_id": processor_id, "status": status, "item_index": item_index}
    return append(storage, stream_id, event=f"handoff_{status}", payload=event_payload, guard=validate_transition)


def record_wipe_confirmed(storage, stream_id: str, payload: dict | None = None, *, item_index: int = 0) -> dict:
    """Records the data_wipe_confirmed event that unblocks a storage device."""
    return append(storage, stream_id, event="data_wipe_confirmed", payload={**(payload or {}), "item_index": item_index})
