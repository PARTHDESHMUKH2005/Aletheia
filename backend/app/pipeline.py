"""run_pipeline(stream_id): the one function that runs locally and on Lambda,
unchanged either way (BUILD.md section 2/9). Idempotent: exits if the stream's
status is already past SUBMITTED. Per-step timing logs, one JSON line each.
"""
import json
import logging
import time
from pathlib import Path

from app.models import Characterization
from app.tools.characterize import PhotoBlock, characterize_waste
from app.tools.guardrails import out_of_scope_flag
from app.tools.ledger import record_handoff
from app.tools.matching import find_processors
from app.tools.report import counterfactual_receipt

logger = logging.getLogger("loopback.pipeline")

_DATA_DIR = Path(__file__).resolve().parent / "data"
_ORGS: dict[str, dict] = {row["id"]: row for row in json.loads((_DATA_DIR / "orgs.json").read_text())}

LOW_CONFIDENCE_THRESHOLD = 0.7
HAZARDOUS_CONFIDENCE_THRESHOLD = 0.85


def _guess_format(key: str) -> str:
    ext = key.rsplit(".", 1)[-1].lower() if "." in key else "jpeg"
    return "jpeg" if ext == "jpg" else ext


def run_pipeline(stream_id: str, storage=None) -> dict:
    if storage is None:
        from app.config import get_storage
        storage = get_storage()

    stream = storage.get_stream(stream_id)
    if stream is None:
        raise KeyError(f"no such stream: {stream_id}")

    if stream["status"] != "SUBMITTED":
        logger.info(json.dumps({"step": "pipeline", "stream_id": stream_id, "skipped": True, "status": stream["status"]}))
        return stream

    storage.update_stream(stream_id, status="CHARACTERIZING")
    timings: dict[str, int] = {}

    try:
        t0 = time.monotonic()
        photos: list[PhotoBlock] = [
            {"format": _guess_format(key), "bytes": storage.read_upload(key)}
            for key in stream["photo_keys"]
        ]
        characterization = characterize_waste(
            photos, note=stream.get("note", ""), quantity_kg=stream.get("quantity_kg"), storage=storage,
        )
        timings["characterize_ms"] = int((time.monotonic() - t0) * 1000)

        org = _ORGS.get(stream["org_id"])
        org_location = org["location"] if org else {"lat": None, "lng": None}
        slider_w = stream.get("slider_w", 0.5)

        t1 = time.monotonic()
        routings = []
        receipts = []
        needs_review = False
        refused = False

        for item in characterization.items:
            scope_flag = out_of_scope_flag(item)
            if scope_flag:
                refused = True
                routings.append({"refused": True, "out_of_scope_category": scope_flag})
                receipts.append(None)
                continue

            threshold = HAZARDOUS_CONFIDENCE_THRESHOLD if item.hazardous else LOW_CONFIDENCE_THRESHOLD
            if item.confidence < threshold:
                needs_review = True

            routing_result = find_processors(item, org_location, w=slider_w)
            if routing_result["review_required"]:
                needs_review = True

            receipt = counterfactual_receipt(item, routing_result)
            routings.append(routing_result)
            receipts.append(receipt.model_dump())

            picked_id = routing_result.get("picked_processor_id") or routing_result.get("reuse_recommended_processor_id")
            if picked_id is not None:
                record_handoff(storage, stream_id, picked_id, "requested", item)

        timings["routing_ms"] = int((time.monotonic() - t1) * 1000)

        if refused:
            status = "NEEDS_REVIEW"
        elif needs_review or characterization.overall_confidence < LOW_CONFIDENCE_THRESHOLD:
            status = "NEEDS_REVIEW"
        else:
            status = "ROUTED"

        storage.update_stream(
            stream_id,
            status=status,
            characterization=characterization.model_dump(),
            routing=routings,
            receipts=receipts,
            timings=timings,
        )
        logger.info(json.dumps({"step": "pipeline", "stream_id": stream_id, "status": status, **timings}))
        return storage.get_stream(stream_id)

    except Exception as exc:
        storage.update_stream(stream_id, status="FAILED", error=str(exc))
        logger.info(json.dumps({"step": "pipeline", "stream_id": stream_id, "status": "FAILED", "error": str(exc)}))
        raise
