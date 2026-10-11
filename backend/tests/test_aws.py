"""Exercise cloud storage and Lambda dispatch without contacting AWS or an LLM."""
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import boto3
import pytest
from botocore.config import Config
from botocore.exceptions import ClientError
from botocore.stub import Stubber
from fastapi import BackgroundTasks
from moto import mock_aws

from app import lambda_pipeline, worker
from app.config import get_settings
from app.storage.aws import AwsStorage
from app.tools import ledger
from tests.helpers import JPEG_BYTES


@pytest.fixture
def cloud(monkeypatch):
    for key, value in {"AWS_DEFAULT_REGION": "us-east-1", "AWS_ACCESS_KEY_ID": "testing",
                       "AWS_SECRET_ACCESS_KEY": "testing", "BUCKET": "loopback-test-uploads",
                       "STREAMS_TABLE": "streams", "CACHE_TABLE": "cache", "LEDGER_TABLE": "ledger"}.items():
        monkeypatch.setenv(key, value)
    with mock_aws():
        db = boto3.resource("dynamodb")
        db.create_table(TableName="streams", BillingMode="PAY_PER_REQUEST",
            KeySchema=[{"AttributeName": "stream_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "stream_id", "AttributeType": "S"},
                                  {"AttributeName": "org_id", "AttributeType": "S"}],
            GlobalSecondaryIndexes=[{"IndexName": "org-index", "KeySchema": [
                {"AttributeName": "org_id", "KeyType": "HASH"}, {"AttributeName": "stream_id", "KeyType": "RANGE"}],
                "Projection": {"ProjectionType": "ALL"}}])
        db.create_table(TableName="cache", BillingMode="PAY_PER_REQUEST",
            KeySchema=[{"AttributeName": "image_sha", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "image_sha", "AttributeType": "S"}])
        db.create_table(TableName="ledger", BillingMode="PAY_PER_REQUEST",
            KeySchema=[{"AttributeName": "chain_id", "KeyType": "HASH"}, {"AttributeName": "link_no", "KeyType": "RANGE"}],
            AttributeDefinitions=[{"AttributeName": "chain_id", "AttributeType": "S"},
                                  {"AttributeName": "link_no", "AttributeType": "N"}])
        s3 = boto3.client("s3", config=Config(signature_version="s3v4"))
        s3.create_bucket(Bucket="loopback-test-uploads")
        yield AwsStorage(db, s3)


def test_cloud_stream_crud_and_org_isolation(cloud):
    cloud.create_stream("one", {"org_id": "workshop", "status": "SUBMITTED", "quantity": 0.5})
    cloud.create_stream("two", {"org_id": "lab", "status": "SUBMITTED"})
    with pytest.raises(ClientError):
        cloud.create_stream("one", {"org_id": "lab"})
    cloud.update_stream("one", status="ROUTED")
    assert cloud.get_stream("one")["status"] == "ROUTED"
    assert cloud.get_stream("one")["quantity"] == 0.5
    assert cloud.get_stream("missing") is None
    assert [s["stream_id"] for s in cloud.list_streams_by_org("workshop")] == ["one"]
    with pytest.raises(KeyError):
        cloud.update_stream("missing", status="ROUTED")


def test_cloud_cache_expiry_and_json_roundtrip(cloud):
    cloud.set_cached_characterization("hash", {"items": [{"confidence": 0.9}]})
    assert cloud.get_cached_characterization("hash")["items"][0]["confidence"] == 0.9
    cloud.cache.update_item(Key={"image_sha": "hash"}, UpdateExpression="SET #ttl = :expired",
        ExpressionAttributeNames={"#ttl": "ttl"}, ExpressionAttributeValues={":expired": 1})
    assert cloud.get_cached_characterization("hash") is None


def test_cloud_ledger_uniqueness_verification_and_tamper_gate(cloud, monkeypatch):
    first = ledger.append(cloud, "one", "characterized", {"confidence": 0.9})
    ledger.append(cloud, "one", "route_selected", {"item_index": 0})
    assert not cloud.append_ledger_entry(first)
    assert cloud.get_ledger_head("one")["link_no"] == 2
    assert ledger.verify(cloud, "one") == {"ok": True, "links": 2, "first_broken": None}
    monkeypatch.setenv("ENV", "production")
    get_settings.cache_clear()
    with pytest.raises(PermissionError):
        cloud.tamper_ledger_entry_for_demo("one", 1)
    monkeypatch.setenv("ENV", "local")
    get_settings.cache_clear()
    assert cloud.tamper_ledger_entry_for_demo("one", 1)
    assert not ledger.verify(cloud, "one")["ok"]
    with pytest.raises(PermissionError):
        ledger.append(cloud, "one", "data_wipe_confirmed", {})


def test_cloud_private_uploads_missing_size_and_oversized_reads(cloud):
    key = "workshop/photo.jpg"
    cloud.save_upload(key, JPEG_BYTES)
    assert cloud.read_upload(key) == JPEG_BYTES
    assert "loopback-test-uploads" in cloud.upload_url(key, len(JPEG_BYTES))
    with pytest.raises(ValueError):
        cloud.upload_url(key)
    with pytest.raises(FileNotFoundError):
        cloud.read_upload("workshop/missing.jpg")
    with pytest.raises(ValueError):
        cloud.save_upload("../escape.jpg", JPEG_BYTES)
    cloud.s3.put_object(Bucket=cloud.bucket, Key=key, Body=b"x" * (5 * 1024 * 1024 + 1))
    with pytest.raises(ValueError):
        cloud.read_upload(key)


def test_cloud_uploads_are_create_once_and_presign_requires_condition(cloud):
    key = "workshop/photo.jpg"
    cloud.save_upload(key, JPEG_BYTES)
    with pytest.raises(FileExistsError):
        cloud.save_upload(key, b"replacement")
    assert cloud.read_upload(key) == JPEG_BYTES
    query = parse_qs(urlsplit(cloud.upload_url(key, len(JPEG_BYTES))).query)
    assert "if-none-match" in query["X-Amz-SignedHeaders"][0].split(";")


def test_cloud_queries_follow_all_pages():
    responses = iter([{"Items": [1], "LastEvaluatedKey": {"id": "one"}}, {"Items": [2]}])
    calls = []
    def query(**params):
        calls.append(params)
        return next(responses)
    assert AwsStorage._query(SimpleNamespace(query=query), IndexName="org-index") == [1, 2]
    assert calls[1]["ExclusiveStartKey"] == {"id": "one"}


def test_worker_dispatch_is_async_and_contains_only_stream_id(cloud, monkeypatch):
    monkeypatch.setenv("STORAGE", "aws")
    monkeypatch.setenv("PIPELINE_FN", "test-pipeline")
    get_settings.cache_clear()
    client = boto3.client("lambda")
    monkeypatch.setattr(boto3, "client", lambda service: client)
    with Stubber(client) as stub:
        stub.add_response("invoke", {"StatusCode": 202}, {"FunctionName": "test-pipeline",
            "InvocationType": "Event", "Payload": json.dumps({"stream_id": "one"}).encode()})
        tasks = BackgroundTasks()
        worker.enqueue_pipeline("one", tasks)
        assert not tasks.tasks
        stub.assert_no_pending_responses()


def test_local_worker_uses_background_tasks():
    tasks = BackgroundTasks()
    worker.enqueue_pipeline("one", tasks)
    assert tasks.tasks[0].args == ("one",)


@pytest.mark.parametrize("budget,final_status", [(1000, "FAILED"), (180000, "ROUTED")])
def test_lambda_worker_persists_budget_failures_and_preserves_completed_results(cloud, monkeypatch, budget, final_status):
    cloud.create_stream("one", {"org_id": "workshop", "status": "SUBMITTED"})
    monkeypatch.setattr(lambda_pipeline, "get_storage", lambda: cloud)
    def process(*args, **kwargs):
        cloud.update_stream("one", status="ROUTED")
        raise TimeoutError("optional summary timed out")
    monkeypatch.setattr(lambda_pipeline, "run_pipeline", process)
    assert lambda_pipeline.handler({"stream_id": "one"}, SimpleNamespace(
        get_remaining_time_in_millis=lambda: budget))["status"] == final_status
    assert cloud.get_stream("one")["status"] == final_status


def test_sam_template_transforms_offline(monkeypatch):
    from samtranslator.translator.transform import transform
    from samtranslator.yaml_helper import yaml_parse
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    template = yaml_parse((Path(__file__).resolve().parents[2] / "infra" / "template.yaml").read_text())
    # SAM CLI resolves local CodeUri during packaging; the translator receives an S3 URI.
    assert (Path(__file__).resolve().parents[2] / "infra" / template["Globals"]["Function"]["CodeUri"]).is_dir()
    template["Globals"]["Function"]["CodeUri"] = "s3://offline-test/code.zip"
    policies = SimpleNamespace(load=lambda: {
        "AWSLambdaBasicExecutionRole": "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"})
    result = transform(template, {"GeminiApiKey": "fake", "ApiTokensJson": "[]"}, policies)
    resources = result["Resources"]
    assert resources["ApiFunction"]["Type"] == "AWS::Lambda::Function"
    assert resources["PipelineFunction"]["Properties"]["Timeout"] == 180
    assert resources["UploadBucket"]["Properties"]["PublicAccessBlockConfiguration"]["BlockPublicPolicy"]
    assert resources["ApiFunction"]["Properties"]["Environment"]["Variables"]["ENV"] == "production"
