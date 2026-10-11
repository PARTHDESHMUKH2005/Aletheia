"""run_pipeline(stream_id): the one function that runs locally and on Lambda,
unchanged either way (BUILD.md section 2/9). Idempotent: exits if the stream's
status is already past SUBMITTED. Per-step timing logs, one JSON line each.
"""
import json
import logging
import time

from app.agent import RunContext, hand_off, route_item, routed_processor_id, run_characterize, run_orchestrator
from app.config import get_settings
from app.tools.assessment import assess_item
from app.tools.characterize import characterize_waste
from app.tools.geo import LocationError, resolve_pincode
from app.tools.report import counterfactual_receipt

logger = logging.getLogger("loopback.pipeline")


LOW_CONFIDENCE_THRESHOLD = 0.7
HAZARDOUS_CONFIDENCE_THRESHOLD = 0.85


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
        ctx = RunContext(
            storage=storage, stream_id=stream_id, stream=stream, org_location=org_location,
            slider_w=stream.get("slider_w", 0.5), characterize_fn=characterize_waste,
        )

        # The orchestrator agent drives the tools; it is optional (USE_AGENT) and best-effort.
        # Whatever it did or skipped, the loop below completes and re-checks every item in
        # plain code, so the stored result never depends on the model behaving.
        agent_run = None
        if get_settings().use_agent:
            t_agent = time.monotonic()
            agent_run = run_orchestrator(ctx)
            timings["agent_ms"] = int((time.monotonic() - t_agent) * 1000)

        characterization = run_characterize(ctx)
        timings["characterize_ms"] = ctx.characterize_ms

        t1 = time.monotonic()
        routings = []
        receipts = []
        assessments = []
        needs_review = False
        refused = False

        for index, item in enumerate(characterization.items):
            routing_result = route_item(ctx, index)
            assessments.append(assess_item(item))

            if routing_result.get("refused"):
                refused = True
                routings.append(routing_result)
                receipts.append(None)
                continue

            threshold = HAZARDOUS_CONFIDENCE_THRESHOLD if item.hazardous else LOW_CONFIDENCE_THRESHOLD
            if item.confidence < threshold:
                needs_review = True
            if routing_result["review_required"]:
                needs_review = True

            routings.append(routing_result)
            receipts.append(counterfactual_receipt(item, routing_result).model_dump())

            picked_id = routed_processor_id(routing_result)
            if picked_id is not None:
                hand_off(ctx, index, picked_id)

        timings["routing_ms"] = int((time.monotonic() - t1) * 1000)

        if refused:
            status = "NEEDS_REVIEW"
        elif needs_review or characterization.overall_confidence < LOW_CONFIDENCE_THRESHOLD:
            status = "NEEDS_REVIEW"
        else:
            status = "ROUTED"

        extra = {}
        if agent_run is not None:
            extra["agent"] = {k: v for k, v in agent_run.items() if k in ("summary", "error", "tool_calls", "usage")}
        storage.update_stream(
            stream_id,
            status=status,
            characterization=characterization.model_dump(),
            routing=routings,
            receipts=receipts,
            assessments=assessments,
            timings=timings,
            **extra,
        )
        logger.info(json.dumps({"step": "pipeline", "stream_id": stream_id, "status": status, **timings}))
        return storage.get_stream(stream_id)

    except LocationError as exc:
        return _fail_with_user_message(storage, stream_id, exc)

    except Exception as exc:
        storage.update_stream(stream_id, status="FAILED", error=str(exc))
        logger.info(json.dumps({"step": "pipeline", "stream_id": stream_id, "status": "FAILED", "error": str(exc)}))
        raise
