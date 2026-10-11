"""FastAPI app: all endpoints from BUILD.md section 2, plus the slider-parameterized
/route endpoint and the draft-pickup-message endpoint from the feature spec. Same
app runs locally and in the api Lambda (via Mangum) -- Mangum wiring is Phase 3.
Local worker is BackgroundTasks; no AWS code here.
"""
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings, get_storage
from app.models import (
    Item,
    StreamCreateRequest,
    StreamCreateResponse,
    UploadRequest,
    UploadTarget,
    VerifyResponse,
    WipeConfirmResponse,
)
from app.pipeline import run_pipeline
from datetime import datetime, timezone

from pydantic import BaseModel

from app.tools import ewaste, ledger, report
from app.tools.assessment import assess_item
from app.tools.geo import LocationError, resolve_pincode
from app.tools.guardrails import authorization_label
from app.tools.matching import SCORING_CONFIG, find_processors

_DATA_DIR = Path(__file__).resolve().parent / "data"
_PROCESSORS: list[dict] = json.loads((_DATA_DIR / "processors.json").read_text())
_ORGS: dict[str, dict] = {row["id"]: row for row in json.loads((_DATA_DIR / "orgs.json").read_text())}

ROUTING_DISCLAIMER = (
    "Routing aid only. Confirm rules and processor authorization with the "
    "official CPCB or State Board source."
)

app = FastAPI(title="LoopBack")

# The React (Vite) dev server runs on a different origin (localhost:5173) than
# this API (localhost:8000), unlike the single-page /demo/ mount below which is
# same-origin. Override with FRONTEND_ORIGIN (comma-separated) before deploying.
_FRONTEND_ORIGINS = [o.strip() for o in os.environ.get(
    "FRONTEND_ORIGIN", "http://localhost:5173,http://127.0.0.1:5173"
).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_FRONTEND_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _storage():
    return get_storage()


def _get_stream_or_404(storage, stream_id: str) -> dict:
    stream = storage.get_stream(stream_id)
    if stream is None:
        raise HTTPException(status_code=404, detail="stream not found")
    return stream


@app.post("/uploads")
def create_upload_targets(body: UploadRequest) -> list[UploadTarget]:
    targets = []
    for _ in range(body.count):
        key = f"{uuid.uuid4().hex}.jpg"
        targets.append(UploadTarget(key=key, url=f"/local-uploads/{key}"))
    return targets


@app.put("/local-uploads/{key}")
async def put_local_upload(key: str, request: Request) -> dict:
    """Local stand-in for a presigned S3 PUT URL (BUILD.md section 2, step 2)."""
    data = await request.body()
    _storage().save_upload(key, data)
    return {"ok": True, "key": key}


@app.get("/local-uploads/{key}")
def get_local_upload(key: str) -> Response:
    """Serves an uploaded photo so the passport can show it (local dev stand-in for an S3 URL)."""
    if not re.fullmatch(r"[A-Za-z0-9._-]+", key):
        raise HTTPException(status_code=404, detail="no such upload")
    try:
        data = _storage().read_upload(key)
    except (FileNotFoundError, KeyError):
        raise HTTPException(status_code=404, detail="no such upload")
    return Response(content=data, media_type="image/jpeg")


@app.post("/streams", status_code=202)
def create_stream(body: StreamCreateRequest, background_tasks: BackgroundTasks) -> StreamCreateResponse:
    if body.org_id not in _ORGS:
        raise HTTPException(status_code=404, detail=f"no such org: {body.org_id}")
    try:
        resolve_pincode(body.pincode)
    except LocationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    stream_id = uuid.uuid4().hex
    storage = _storage()
    storage.create_stream(stream_id, {
        "org_id": body.org_id,
        "note": body.note,
        "quantity_kg": body.quantity_kg,
        "photo_keys": body.photo_keys,
        "pincode": body.pincode,
        "slider_w": 0.5,
        "status": "SUBMITTED",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    # No storage object is passed into the background task: a SQLite connection
    # created in this request's thread shouldn't be reused from the task's thread.
    # run_pipeline(storage=None) opens its own connection to the same local DB file.
    background_tasks.add_task(run_pipeline, stream_id)
    return StreamCreateResponse(stream_id=stream_id)


@app.get("/streams/{stream_id}")
def get_stream(stream_id: str) -> dict:
    storage = _storage()
    stream = _get_stream_or_404(storage, stream_id)
    stream = dict(stream)
    stream["stream_id"] = stream_id
    stream["ledger"] = storage.get_ledger_chain(stream_id)
    try:
        stream["pickup_location"] = resolve_pincode(stream.get("pincode"))
    except LocationError:
        stream["pickup_location"] = None
    stream["org_name"] = _ORGS.get(stream.get("org_id"), {}).get("name")
    return stream


@app.get("/streams/{stream_id}/route")
def get_route(stream_id: str, w: float = 0.5, item_index: int = 0, evidence_weight: float = 0.0) -> dict:
    """The slider endpoint: re-ranks processors for item_index at the given w and
    returns the ranked list, the pick, the trade-off explanation, and the receipt.
    """
    storage = _storage()
    stream = _get_stream_or_404(storage, stream_id)
    if not 0.0 <= w <= 1.0:
        raise HTTPException(status_code=422, detail="w must be between 0 and 1")
    if not 0.0 <= evidence_weight <= 1.0:
        raise HTTPException(status_code=422, detail="evidence_weight must be between 0 and 1")

    characterization = stream.get("characterization")
    if not characterization:
        raise HTTPException(status_code=409, detail="stream not characterized yet")
    items = characterization["items"]
    if item_index < 0 or item_index >= len(items):
        raise HTTPException(status_code=404, detail="no such item_index")

    item = Item.model_validate(items[item_index])
    try:
        routing_result = find_processors(item, resolve_pincode(stream.get("pincode")), w=w, evidence_weight=evidence_weight)
    except LocationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    receipt = report.counterfactual_receipt(item, routing_result)
    return {"routing": routing_result, "receipt": receipt.model_dump(), "assessment": assess_item(item)}


@app.post("/streams/{stream_id}/wipe")
def confirm_wipe(stream_id: str) -> WipeConfirmResponse:
    storage = _storage()
    _get_stream_or_404(storage, stream_id)
    ledger.record_wipe_confirmed(storage, stream_id, payload={"simulated_certificate": True})
    return WipeConfirmResponse(ok=True)


@app.post("/streams/{stream_id}/draft-message")
def draft_pickup_message(stream_id: str, processor_id: str, item_index: int = 0) -> dict:
    """Feature spec section 3 (draft pickup message). The agent never sends this --
    it only records a 'pickup_requested' ledger entry and returns the draft text.
    """
    storage = _storage()
    stream = _get_stream_or_404(storage, stream_id)
    characterization = stream.get("characterization")
    if not characterization:
        raise HTTPException(status_code=409, detail="stream not characterized yet")
    items = characterization["items"]
    if item_index < 0 or item_index >= len(items):
        raise HTTPException(status_code=404, detail="no such item_index")

    processor = next((p for p in _PROCESSORS if p["id"] == processor_id), None)
    if processor is None:
        raise HTTPException(status_code=404, detail="no such processor")

    item_data = items[item_index]
    quantity = item_data.get("quantity_kg")
    quantity_text = f"~{quantity} kg" if quantity is not None else "quantity not stated"
    pincode = stream.get("pincode") or "pincode not given"
    draft_message = (
        f"Pickup request for {processor['name']}: {item_data['material']} ({quantity_text}), "
        f"pickup location pincode {pincode}. Requested pickup window: next business day. "
        f"-- sent via LoopBack on behalf of {stream['org_id']}."
    )

    ledger.append(storage, stream_id, event="pickup_requested", payload={
        "processor_id": processor_id,
        "item_index": item_index,
        "draft_message": draft_message,
        "sent": False,
    })

    return {
        "draft_message": draft_message,
        "label": "Draft only. Not sent. A live version would send this through the buyer's account.",
        "sent": False,
    }


@app.get("/streams/{stream_id}/report")
def get_report(stream_id: str) -> dict:
    """PDF export is not built yet (feature spec item 6, optional/stretch). Returns
    the same receipt data a PDF would render, as JSON, so the endpoint is usable now.
    """
    storage = _storage()
    stream = _get_stream_or_404(storage, stream_id)
    return {
        "stream_id": stream_id,
        "status": stream["status"],
        "receipts": stream.get("receipts"),
        "note": "PDF export not implemented yet; returning the receipt data as JSON instead.",
    }


@app.get("/orgs/{org_id}/dashboard")
def org_dashboard(org_id: str) -> dict:
    if org_id not in _ORGS:
        raise HTTPException(status_code=404, detail=f"no such org: {org_id}")
    storage = _storage()
    streams = storage.list_streams_by_org(org_id)
    ledgers = {s["stream_id"]: storage.get_ledger_chain(s["stream_id"]) for s in streams}
    return report.org_impact(streams, ledgers)


@app.get("/scoring-config")
def scoring_config() -> dict:
    """The exact numbers the routing score uses, so a decision can be checked by hand."""
    return SCORING_CONFIG


class ReviewRequest(BaseModel):
    decision: str            # "confirm_routing" | "reclassify" | "reject"
    reviewer: str
    note: str = ""
    material: str | None = None   # required for "reclassify"


@app.get("/review-queue")
def review_queue(org_id: str | None = None) -> list[dict]:
    """Streams waiting on a person: NEEDS_REVIEW with no review decision yet."""
    storage = _storage()
    rows = []
    for oid in ([org_id] if org_id else list(_ORGS)):
        for stream in storage.list_streams_by_org(oid):
            if stream.get("status") != "NEEDS_REVIEW" or stream.get("review"):
                continue
            rows.append({
                "stream_id": stream["stream_id"], "org_id": oid,
                "assessments": stream.get("assessments") or [],
                "materials": [i["material"] for i in (stream.get("characterization") or {}).get("items", [])],
            })
    return rows


@app.post("/streams/{stream_id}/review")
def submit_review(stream_id: str, body: ReviewRequest) -> dict:
    """A person's decision on a NEEDS_REVIEW stream, written to the ledger."""
    storage = _storage()
    stream = _get_stream_or_404(storage, stream_id)
    if stream.get("status") != "NEEDS_REVIEW":
        raise HTTPException(status_code=409, detail="stream is not waiting for review")
    if not body.reviewer.strip():
        raise HTTPException(status_code=422, detail="reviewer is required")
    if body.decision not in ("confirm_routing", "reclassify", "reject"):
        raise HTTPException(status_code=422, detail="decision must be confirm_routing, reclassify or reject")

    items = stream["characterization"]["items"]
    routings = list(stream.get("routing") or [])
    receipts = list(stream.get("receipts") or [])
    assessments = list(stream.get("assessments") or [])
    new_status = "ROUTED"
    payload = {"reviewer": body.reviewer.strip(), "decision": body.decision, "note": body.note}

    if body.decision == "reject":
        new_status = "REJECTED"
    elif any(r and r.get("refused") for r in routings):
        raise HTTPException(status_code=409, detail="an item is out of scope; it can only be rejected")
    elif body.decision == "reclassify":
        valid = set(Item.model_fields["material"].annotation.__args__)
        if body.material not in valid:
            raise HTTPException(status_code=422, detail=f"material must be one of {sorted(valid)}")
        for i, data in enumerate(items):
            items[i] = {**data, "material": body.material, "confidence": 1.0}
        payload["material"] = body.material
        try:
            location = resolve_pincode(stream.get("pincode"))
        except LocationError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        for i, data in enumerate(items):
            item = Item.model_validate(data)
            routing = find_processors(item, location, w=stream.get("slider_w", 0.5))
            routings[i] = routing
            receipts[i] = report.counterfactual_receipt(item, routing).model_dump()
            assessments[i] = assess_item(item)
    else:
        for i, r in enumerate(routings):
            if r and Item.model_validate(items[i]).hazardous and not r.get("picked_processor_id"):
                raise HTTPException(status_code=409, detail="a hazardous item has no authorization-checked buyer; it cannot be confirmed")

    ledger.append(storage, stream_id, event="human_review", payload=payload)
    review = {**payload, "at": datetime.now(timezone.utc).isoformat()}
    storage.update_stream(
        stream_id, status=new_status, review=review,
        characterization={**stream["characterization"], "items": items},
        routing=routings, receipts=receipts, assessments=assessments,
    )
    return {"stream_id": stream_id, "status": new_status, "review": review}


class HandoffRequest(BaseModel):
    status: str
    weight_kg: float | None = None
    processor_id: str | None = None
    item_index: int = 0


@app.post("/streams/{stream_id}/handoff")
def advance_handoff(stream_id: str, body: HandoffRequest) -> dict:
    """Moves a handoff forward (matched, collected, weighed, verified). Blocked while any
    storage drive in an e-waste batch lacks a wipe or destruction record.
    """
    storage = _storage()
    stream = _get_stream_or_404(storage, stream_id)
    if body.status not in ("matched", "collected", "weighed", "verified"):
        raise HTTPException(status_code=422, detail="status must be matched, collected, weighed or verified")
    if stream.get("status") != "ROUTED":
        raise HTTPException(status_code=409, detail="only a ROUTED stream can move through handoff")
    items = stream["characterization"]["items"]
    if not 0 <= body.item_index < len(items):
        raise HTTPException(status_code=404, detail="no such item_index")
    if body.weight_kg is not None and body.weight_kg <= 0:
        raise HTTPException(status_code=422, detail="weight_kg must be positive")

    reasons = ewaste.blocking_reasons(stream.get("ewaste"))
    if reasons:
        raise HTTPException(status_code=409, detail={"blocked": True, "reasons": reasons})

    routing = (stream.get("routing") or [None])[body.item_index] or {}
    processor_id = body.processor_id or routing.get("picked_processor_id") or routing.get("reuse_recommended_processor_id")
    if processor_id is None:
        raise HTTPException(status_code=409, detail="no buyer was picked for this item")
    try:
        entry = ledger.record_handoff(
            storage, stream_id, processor_id, body.status, Item.model_validate(items[body.item_index]),
            payload={"weight_kg": body.weight_kg} if body.weight_kg is not None else None,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"stream_id": stream_id, "status": body.status, "link_no": entry["link_no"]}


class EwasteRegisterRequest(BaseModel):
    devices: list[dict]


class DriveWipeRequest(BaseModel):
    method: str
    certificate_ref: str
    operator: str


@app.post("/streams/{stream_id}/ewaste")
def register_ewaste(stream_id: str, body: EwasteRegisterRequest) -> dict:
    """Records the devices in a retired-equipment batch. Each installed drive becomes its
    own tracked record. Returns the pathway per device (reuse, refurbish or recycle)."""
    storage = _storage()
    stream = _get_stream_or_404(storage, stream_id)
    try:
        batch = ewaste.register_devices(stream.get("ewaste"), body.devices)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    storage.update_stream(stream_id, ewaste=batch)
    ledger.append(storage, stream_id, event="ewaste_devices_registered", payload={
        "asset_tags": [d["asset_tag"] for d in batch["devices"][-len(body.devices):]],
    })
    return ewaste.summarize(batch)


@app.get("/streams/{stream_id}/ewaste")
def get_ewaste(stream_id: str) -> dict:
    return ewaste.summarize(_get_stream_or_404(_storage(), stream_id).get("ewaste"))


@app.post("/streams/{stream_id}/ewaste/drives/{drive_id}/wipe")
def wipe_drive(stream_id: str, drive_id: str, body: DriveWipeRequest) -> dict:
    storage = _storage()
    stream = _get_stream_or_404(storage, stream_id)
    batch = stream.get("ewaste")
    if not batch:
        raise HTTPException(status_code=409, detail="no e-waste batch registered for this stream")
    try:
        ewaste.record_drive_wipe(storage, stream_id, batch, drive_id, body.method, body.certificate_ref, body.operator)
    except KeyError:
        raise HTTPException(status_code=404, detail="no such drive_id")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    storage.update_stream(stream_id, ewaste=batch)
    return ewaste.summarize(batch)


@app.get("/processors")
def list_processors() -> list[dict]:
    return [{**p, "authorization_label": authorization_label(p)} for p in _PROCESSORS]


@app.get("/verify/{chain_id}")
def verify_chain(chain_id: str) -> VerifyResponse:
    result = ledger.verify(_storage(), chain_id)
    return VerifyResponse(**result)


@app.post("/dev/tamper/{chain_id}")
def dev_tamper_ledger(chain_id: str, link_no: int = 1) -> dict:
    """Demo tool only: corrupts one stored ledger entry so /verify turns red.
    Disabled whenever ENV=production (config.dev_tools_enabled).
    """
    if not get_settings().dev_tools_enabled:
        raise HTTPException(status_code=403, detail="dev tools are disabled in this environment")
    tampered = _storage().tamper_ledger_entry_for_demo(chain_id, link_no)
    if not tampered:
        raise HTTPException(status_code=404, detail="no such chain_id/link_no")
    return {"tampered": True, "chain_id": chain_id, "link_no": link_no, "label": "Demo tool only."}


# Minimal single-page demo UI (frontend/demo/index.html), served at /demo/ so it
# never shadows the API routes above. Not the Phase 4 React/Vite app.
_FRONTEND_DEMO_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "demo"
if _FRONTEND_DEMO_DIR.exists():
    app.mount("/demo", StaticFiles(directory=str(_FRONTEND_DEMO_DIR), html=True), name="demo-frontend")
