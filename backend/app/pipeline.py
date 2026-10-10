"""run_pipeline(stream_id): the one function that runs locally and on Lambda,
unchanged either way (BUILD.md section 2/9). Idempotent: exits if the stream's
status is already past SUBMITTED. Per-step timing logs, one JSON line each.
"""
import json
import logging
import time

from app.models import Characterization
from app.tools.assessment import assess_item
from app.tools.characterize import PhotoBlock, characterize_waste
from app.tools.geo import LocationError, resolve_pincode
from app.tools.guardrails import out_of_scope_flag
from app.tools.ledger import record_handoff
from app.tools.matching import find_processors
from app.tools.report import counterfactual_receipt

logger = logging.getLogger("loopback.pipeline")


LOW_CONFIDENCE_THRESHOLD = 0.7
HAZARDOUS_CONFIDENCE_THRESHOLD = 0.85


def _guess_format(key: str) -> str:
    ext = key.rsplit(".", 1)[-1].lower() if "." in key else "jpeg"
    return "jpeg" if ext == "jpg" else ext


def _fail_with_user_message(storage, stream_id: str, exc: LocationError) -> dict:
    """Location problems are the caller's to fix, so the stream is marked FAILED with
    the message as-is (stream["error"]) instead of raising out of the worker.
    """
    storage.update_stream(stream_id, status="FAILED", error=str(exc))
    logger.info(json.dumps({"step": "pipeline", "stream_id": stream_id, "status": "FAILED", "error": str(exc)}))
    return storage.get_stream(stream_id)


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

    # The pickup point comes from the request's pincode (demo table only, no external
    # geocoder). Resolved before the model call so a bad pincode costs nothing.
    try:
        org_location = resolve_pincode(stream.get("pincode"))
    except LocationError as exc:
        return _fail_with_user_message(storage, stream_id, exc)

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

        slider_w = stream.get("slider_w", 0.5)

        t1 = time.monotonic()
        routings = []
        receipts = []
        assessments = []
        needs_review = False
        refused = False

        for item in characterization.items:
            scope_flag = out_of_scope_flag(item)
            if scope_flag:
                refused = True
                routings.append({"refused": True, "out_of_scope_category": scope_flag})
                receipts.append(None)
                assessments.append(assess_item(item))
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
            assessments.append(assess_item(item))

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
            assessments=assessments,
            timings=timings,
        )
        logger.info(json.dumps({"step": "pipeline", "stream_id": stream_id, "status": status, **timings}))
        return storage.get_stream(stream_id)

    except LocationError as exc:
        return _fail_with_user_message(storage, stream_id, exc)

    except Exception as exc:
        storage.update_stream(stream_id, status="FAILED", error=str(exc))
        logger.info(json.dumps({"step": "pipeline", "stream_id": stream_id, "status": "FAILED", "error": str(exc)}))
        raise
