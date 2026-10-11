"""Opaque bearer credentials scoped to organizations and server-assigned roles."""
import hashlib
import hmac
import json
import os
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_storage
from app.uploads import validate_upload_key

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    subject: str
    org_ids: tuple[str, ...]
    role: str

    def require_org(self, org_id: str) -> None:
        if org_id not in self.org_ids:
            raise HTTPException(403, "organization access denied")

    def require_role(self, *roles: str) -> None:
        if self.role not in roles:
            raise HTTPException(403, "this action requires a reviewer or administrator")


def get_principal(request: Request) -> Principal:
    return request.state.principal


def authorize_request(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)):
    path = request.url.path
    if request.method == "GET" and (path.startswith("/verify/") or path in ("/processors", "/scoring-config")):
        return
    if credentials is None:
        raise HTTPException(401, "bearer credential required", headers={"WWW-Authenticate": "Bearer"})
    try:
        entries = json.loads(os.environ.get("API_TOKENS_JSON", "[]"))
        if not isinstance(entries, list) or not entries:
            raise ValueError
        principal = None
        digest = hashlib.sha256(credentials.credentials.encode()).digest()
        for entry in entries:
            if (not isinstance(entry.get("token"), str) or len(entry["token"]) < 20
                    or not isinstance(entry.get("subject"), str) or not entry["subject"].strip()
                    or entry.get("role") not in ("operator", "reviewer", "admin")
                    or not isinstance(entry.get("org_ids"), list) or not entry["org_ids"]
                    or not all(isinstance(org, str) for org in entry["org_ids"])):
                raise ValueError
            if hmac.compare_digest(digest, hashlib.sha256(entry["token"].encode()).digest()):
                principal = Principal(entry["subject"], tuple(entry["org_ids"]), entry["role"])
        if principal is None:
            raise HTTPException(401, "invalid bearer credential", headers={"WWW-Authenticate": "Bearer"})
    except (ValueError, TypeError, KeyError, AttributeError):
        raise HTTPException(503, "API credentials are not configured correctly") from None
    request.state.principal = principal
    params = request.path_params
    if path.startswith("/dev/") and params.get("chain_id"):
        stream = get_storage().get_stream(params["chain_id"])
        if stream is None:
            raise HTTPException(404, "stream not found")
        principal.require_org(stream["org_id"])
    if params.get("org_id"):
        principal.require_org(params["org_id"])
    if params.get("stream_id"):
        storage = get_storage()
        stream = storage.get_stream(params["stream_id"])
        if stream is None:
            raise HTTPException(404, "stream not found")
        principal.require_org(stream["org_id"])
        if request.method != "GET" and storage.get_ledger_head(params["stream_id"]):
            from app.tools.ledger import verify
            if not verify(storage, params["stream_id"])["ok"]:
                raise HTTPException(409, "ledger is damaged or uses the legacy hash format")
    if params.get("key"):
        try:
            validate_upload_key(params["key"])
            org_id, _ = params["key"].split("/", 1)
        except ValueError:
            raise HTTPException(404, "no such upload") from None
        principal.require_org(org_id)
    if path == "/review-queue" or path.endswith("/review") or path.endswith("/wipe"):
        principal.require_role("reviewer", "admin")
    if path.startswith("/dev/"):
        principal.require_role("admin")

