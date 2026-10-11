"""Run a submitted stream, leaving time to persist failure before Lambda terminates."""
import signal

from app.config import get_storage
from app.pipeline import run_pipeline


def handler(event, context):
    stream_id = event["stream_id"]
    storage = get_storage()
    budget = context.get_remaining_time_in_millis() / 1000 - 5
    if budget <= 0:
        storage.update_stream(stream_id, status="FAILED", error="Processing time budget exhausted", retryable=True)
        return {"stream_id": stream_id, "status": "FAILED"}

    def timeout(signum, frame):
        raise TimeoutError("Processing time budget exhausted")

    previous = signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, budget)
    try:
        result = run_pipeline(stream_id, storage=storage)
        return {"stream_id": stream_id, "status": result["status"]}
    except TimeoutError:
        stream = storage.get_stream(stream_id)
        if stream and stream["status"] in ("SUBMITTED", "CHARACTERIZING", "FAILED"):
            storage.update_stream(stream_id, status="FAILED", error="Processing time budget exhausted", retryable=True)
        return {"stream_id": stream_id, "status": storage.get_stream(stream_id)["status"]}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
