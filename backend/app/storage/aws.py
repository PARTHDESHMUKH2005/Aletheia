"""DynamoDB streams/cache/ledger and private S3 uploads, behind Storage."""
import json
import os
import time

import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config
from botocore.exceptions import ClientError

from app.storage.base import Storage
from app.uploads import MAX_UPLOAD_BYTES, validate_upload_key


class AwsStorage(Storage):
    def __init__(self, dynamodb=None, s3=None):
        self.bucket = os.environ["BUCKET"]
        dynamodb = dynamodb or boto3.resource("dynamodb")
        self.streams = dynamodb.Table(os.environ["STREAMS_TABLE"])
        self.cache = dynamodb.Table(os.environ["CACHE_TABLE"])
        self.ledger = dynamodb.Table(os.environ["LEDGER_TABLE"])
        self.s3 = s3 or boto3.client("s3", config=Config(signature_version="s3v4"))

    def create_stream(self, stream_id, data):
        self.streams.put_item(Item={"stream_id": stream_id, "org_id": data["org_id"],
            "data": json.dumps(data, allow_nan=False), "revision": 0},
            ConditionExpression="attribute_not_exists(stream_id)")

    def get_stream(self, stream_id):
        row = self.streams.get_item(Key={"stream_id": stream_id}, ConsistentRead=True).get("Item")
        return json.loads(row["data"]) if row else None

    def update_stream(self, stream_id, **fields):
        row = self.streams.get_item(Key={"stream_id": stream_id}, ConsistentRead=True).get("Item")
        if not row:
            raise KeyError(f"no such stream: {stream_id}")
        data = {**json.loads(row["data"]), **fields}
        self.streams.put_item(Item={"stream_id": stream_id, "org_id": data["org_id"],
            "data": json.dumps(data, allow_nan=False), "revision": int(row["revision"]) + 1},
            ConditionExpression="revision = :previous",
            ExpressionAttributeValues={":previous": row["revision"]})

    def get_cached_characterization(self, image_sha):
        row = self.cache.get_item(Key={"image_sha": image_sha}).get("Item")
        if not row or int(row["ttl"]) <= time.time():
            return None
        return json.loads(row["characterization"])

    def set_cached_characterization(self, image_sha, characterization):
        self.cache.put_item(Item={"image_sha": image_sha, "characterization": json.dumps(characterization, allow_nan=False),
                                 "ttl": int(time.time()) + 7 * 86400})

    def get_ledger_head(self, chain_id):
        rows = self.ledger.query(KeyConditionExpression=Key("chain_id").eq(chain_id),
            ScanIndexForward=False, Limit=1, ConsistentRead=True)["Items"]
        return self._entry(rows[0]) if rows else None

    def append_ledger_entry(self, entry):
        try:
            self.ledger.put_item(Item=entry,
                ConditionExpression="attribute_not_exists(chain_id) AND attribute_not_exists(link_no)")
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise

    def get_ledger_chain(self, chain_id):
        return [self._entry(row) for row in self._query(self.ledger,
            KeyConditionExpression=Key("chain_id").eq(chain_id), ScanIndexForward=True, ConsistentRead=True)]

    def list_streams_by_org(self, org_id):
        return [{"stream_id": row["stream_id"], **json.loads(row["data"])} for row in self._query(self.streams,
            IndexName="org-index", KeyConditionExpression=Key("org_id").eq(org_id))]

    def tamper_ledger_entry_for_demo(self, chain_id, link_no):
        from app.config import get_settings
        if not get_settings().dev_tools_enabled:
            raise PermissionError("dev tools are disabled")
        try:
            self.ledger.update_item(Key={"chain_id": chain_id, "link_no": link_no},
                UpdateExpression="SET payload_json = :payload",
                ExpressionAttributeValues={":payload": json.dumps({"tampered_by": "demo tool"})},
                ConditionExpression="attribute_exists(chain_id) AND attribute_exists(link_no)")
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise

    def upload_url(self, key, size=None):
        validate_upload_key(key)
        if size is None or not 0 < size <= MAX_UPLOAD_BYTES:
            raise ValueError("a size between 1 byte and 5 MiB is required")
        return self.s3.generate_presigned_url("put_object", Params={"Bucket": self.bucket,
            "Key": key, "ContentType": "image/jpeg", "ContentLength": size, "IfNoneMatch": "*"}, ExpiresIn=300)

    def save_upload(self, key, data):
        validate_upload_key(key)
        if not data or len(data) > MAX_UPLOAD_BYTES:
            raise ValueError("invalid upload size")
        try:
            self.s3.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType="image/jpeg", IfNoneMatch="*")
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("PreconditionFailed", "ConditionalRequestConflict"):
                raise FileExistsError(key) from exc
            raise

    def read_upload(self, key):
        validate_upload_key(key)
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=key, Range=f"bytes=0-{MAX_UPLOAD_BYTES}")
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("NoSuchKey", "404"):
                raise FileNotFoundError(key) from exc
            raise
        with response["Body"] as body:
            data = body.read(MAX_UPLOAD_BYTES + 1)
        if not data or len(data) > MAX_UPLOAD_BYTES:
            raise ValueError("invalid upload size")
        return data

    @staticmethod
    def _entry(row):
        return {**row, "link_no": int(row["link_no"]), "hash_version": int(row.get("hash_version", 1))}

    @staticmethod
    def _query(table, **params):
        rows = []
        while True:
            result = table.query(**params)
            rows.extend(result["Items"])
            if not result.get("LastEvaluatedKey"):
                return rows
            params["ExclusiveStartKey"] = result["LastEvaluatedKey"]
