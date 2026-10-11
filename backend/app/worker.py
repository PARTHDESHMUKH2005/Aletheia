"""Local background execution or asynchronous AWS Lambda dispatch."""
import json
import os

from app.config import get_settings
from app.pipeline import run_pipeline


def enqueue_pipeline(stream_id, background_tasks):
    if get_settings().storage == "local":
        background_tasks.add_task(run_pipeline, stream_id)
        return
    import boto3
    result = boto3.client("lambda").invoke(FunctionName=os.environ["PIPELINE_FN"],
        InvocationType="Event", Payload=json.dumps({"stream_id": stream_id}).encode())
    if result["StatusCode"] != 202:
        raise RuntimeError("pipeline invocation was not accepted")
