"""E-waste batch workflow: device registry, reuse-before-recycle pathway, per-drive data
wipe or destruction records, and the transfer gate.

Policy, not law (see guardrails.STORAGE_DEVICE_POLICY_NOTE): no storage drive leaves the
site until it has a wipe or destruction record. LoopBack stores the record someone
enters; it cannot verify the certificate itself, and says so.
"""
import copy
from datetime import datetime, timezone

from app.tools import ledger

KINDS = ("laptop", "desktop", "server", "monitor", "phone", "network", "printer", "other")
CONDITIONS = ("working", "repairable", "broken", "unknown")
WIPE_METHODS = ("overwrite", "crypto_erase", "degauss", "physical_destruction")

RECORD_NOTE = "Recorded as entered. LoopBack has not independently verified this certificate."

_PATHWAY = {
    "working": ("reuse", "Working: redeploy inside the organization or donate before any recycling."),
    "repairable": ("refurbish", "Repairable: refurbish before recycling."),
    "broken": ("recycle", "Not repairable: recycle through a handler with an authorization reference on file."),
    "unknown": ("inspect", "Condition unknown: test it first, then choose reuse, refurbish or recycle."),
}


def pathway_for(condition: str) -> dict:
    tier, text = _PATHWAY[condition]
    return {"pathway": tier, "pathway_note": text}


def register_devices(existing: dict | None, devices: list[dict]) -> dict:
    """Appends devices (and each installed drive as its own record) to a batch.
    Raises ValueError on a bad kind/condition or a duplicate asset tag.
    """
    # Work on a copy so a bad device mid-list cannot leave the stored batch half-updated.
    batch = copy.deepcopy(existing) if existing else {"devices": [], "drives": []}
    seen = {d["asset_tag"] for d in batch["devices"]}
    for raw in devices:
        tag = (raw.get("asset_tag") or "").strip()
        if not tag:
            raise ValueError("every device needs an asset_tag")
        if tag in seen:
            raise ValueError(f"duplicate asset_tag: {tag}")
        kind, condition = raw.get("kind", "other"), raw.get("condition", "unknown")
        if kind not in KINDS:
            raise ValueError(f"kind must be one of {', '.join(KINDS)}")
        if condition not in CONDITIONS:
            raise ValueError(f"condition must be one of {', '.join(CONDITIONS)}")
        drives = int(raw.get("storage_drives", 0))
        if drives < 0:
            raise ValueError("storage_drives cannot be negative")
        seen.add(tag)
        batch["devices"].append({
            "asset_tag": tag, "kind": kind, "condition": condition,
            "weight_kg": raw.get("weight_kg"), "notes": raw.get("notes", ""),
            "drive_ids": [f"{tag}-D{i}" for i in range(1, drives + 1)],
            **pathway_for(condition),
        })
        for i in range(1, drives + 1):
            batch["drives"].append({"drive_id": f"{tag}-D{i}", "asset_tag": tag, "wipe": None})
    return batch


def record_drive_wipe(storage, stream_id: str, batch: dict, drive_id: str, method: str,
                      certificate_ref: str, operator: str, *, actor: str | None = None) -> dict:
    """Stores the wipe/destruction record on the drive and appends a ledger event."""
    drive = next((d for d in batch["drives"] if d["drive_id"] == drive_id), None)
    if drive is None:
        raise KeyError(drive_id)
    if method not in WIPE_METHODS:
        raise ValueError(f"method must be one of {', '.join(WIPE_METHODS)}")
    if not certificate_ref.strip() or not operator.strip():
        raise ValueError("certificate_ref and operator are both required")
    drive["wipe"] = {
        "method": method, "certificate_ref": certificate_ref.strip(), "operator": operator.strip(),
        "recorded_at": datetime.now(timezone.utc).isoformat(), "note": RECORD_NOTE,
    }
    ledger.append(storage, stream_id, event="data_wipe_confirmed", payload={
        "drive_id": drive_id, "method": method, "certificate_ref": certificate_ref.strip(),
        "operator": operator.strip(), "actor": actor, "note": RECORD_NOTE,
    })
    return drive


def blocking_reasons(batch: dict | None) -> list[str]:
    """Why this batch cannot be handed over yet. Empty list means nothing is blocking."""
    if not batch or not batch["devices"]:
        return []
    return [
        f"drive {d['drive_id']} (device {d['asset_tag']}) has no wipe or destruction record"
        for d in batch["drives"] if d["wipe"] is None
    ]


def summarize(batch: dict | None) -> dict:
    batch = batch or {"devices": [], "drives": []}
    counts = {c: 0 for c in CONDITIONS}
    pathways: dict[str, int] = {}
    for d in batch["devices"]:
        counts[d["condition"]] += 1
        pathways[d["pathway"]] = pathways.get(d["pathway"], 0) + 1
    wiped = sum(1 for d in batch["drives"] if d["wipe"])
    reasons = blocking_reasons(batch)
    return {
        "devices": batch["devices"],
        "drives": batch["drives"],
        "device_count": len(batch["devices"]),
        "by_condition": counts,
        "by_pathway": pathways,
        "drives_total": len(batch["drives"]),
        "drives_with_wipe_record": wiped,
        "transfer_blocked": bool(reasons),
        "blocking_reasons": reasons,
        "policy_note": "LoopBack policy, not a legal requirement: drives stay on site until each has a wipe or destruction record.",
    }
