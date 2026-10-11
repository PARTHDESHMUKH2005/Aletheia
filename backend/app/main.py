"""Organization-scoped FastAPI API, running locally or through Mangum on Lambda."""
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response
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
from pydantic import BaseModel, Field
from typing import Literal

from app.auth import Principal, authorize_request, get_principal
from app.uploads import MAX_UPLOAD_BYTES, validate_image
from app.worker import enqueue_pipeline

from app.tools import ewaste, ledger, report
from app.tools.assessment import assess_item
from app.tools.geo import LocationError, resolve_pincode
from app.tools.guardrails import authorization_label, out_of_scope_flag, processor_authorized_for
from app.tools.matching import SCORING_CONFIG, find_processors

_DATA_DIR = Path(__file__).resolve().parent / "data"
_PROCESSORS: list[dict] = json.loads((_DATA_DIR / "processors.json").read_text())
_ORGS: dict[str, dict] = {row["id"]: row for row in json.loads((_DATA_DIR / "orgs.json").read_text())}

ROUTING_DISCLAIMER = (
    "Routing aid only. Confirm rules and processor authorization with the "
    "official CPCB or State Board source."
)

app = FastAPI(title="LoopBack", dependencies=[Depends(authorize_request)])

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


def _selected_processor(item: Item, routing: dict, requested: str | None = None) -> dict:
    if out_of_scope_flag(item) or routing.get("refused"):
        raise HTTPException(409, "out-of-scope items cannot be handed off")
    picked = routing.get("reuse_recommended_processor_id") or routing.get("picked_processor_id")
    if not picked:
        raise HTTPException(409, "no eligible buyer was selected for this item")
    if requested is not None and requested != picked:
        raise HTTPException(409, "processor must match the saved routing choice")
    processor = next((p for p in _PROCESSORS if p["id"] == picked), None)
    if processor is None or not processor_authorized_for(processor, item.material, item.hazardous):
        raise HTTPException(409, "buyer does not accept this material or lacks checked authorization")
    return processor


@app.get("/session")
def session(principal: Principal = Depends(get_principal)) -> dict:
    orgs = [_ORGS[oid] for oid in principal.org_ids if oid in _ORGS]
    if not orgs:
        raise HTTPException(503, "credential has no configured organization")
    return {"subject": principal.subject, "role": principal.role,
            "orgs": orgs}


@app.post("/uploads")
def create_upload_targets(body: UploadRequest, principal: Principal = Depends(get_principal)) -> list[UploadTarget]:
    principal.require_org(body.org_id)
    if body.org_id not in _ORGS:
        raise HTTPException(404, "no such organization")
    targets = []
    storage = _storage()
    for index in range(body.count):
        key = f"{body.org_id}/{uuid.uuid4().hex}.jpg"
        if get_settings().storage == "aws" and not body.sizes:
            raise HTTPException(422, "provide the size of each resized image")
        size = body.sizes[index] if body.sizes else None
        targets.append(UploadTarget(key=key, url=storage.upload_url(key, size)))
    return targets


@app.put("/local-uploads/{key:path}")
async def put_local_upload(key: str, request: Request) -> dict:
    """Local stand-in for a presigned S3 PUT URL (BUILD.md section 2, step 2)."""
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "photo exceeds 5 MiB")
    try:
        validate_image(bytes(data), key)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    try:
        _storage().save_upload(key, bytes(data))
    except FileExistsError:
        raise HTTPException(409, "photo already uploaded; request a new upload target") from None
    return {"ok": True, "key": key}


@app.get("/local-uploads/{key:path}")
def get_local_upload(key: str) -> Response:
    """Serves an uploaded photo so the passport can show it (local dev stand-in for an S3 URL)."""
    try:
        data = _storage().read_upload(key)
    except (FileNotFoundError, KeyError):
        raise HTTPException(status_code=404, detail="no such upload")
    try:
        mime = validate_image(data)
    except ValueError:
        raise HTTPException(422, "photo is invalid") from None
    return Response(content=data, media_type=mime)


@app.post("/streams", status_code=202)
def create_stream(body: StreamCreateRequest, background_tasks: BackgroundTasks,
                  principal: Principal = Depends(get_principal)) -> StreamCreateResponse:
    if body.org_id not in _ORGS:
        raise HTTPException(status_code=404, detail=f"no such org: {body.org_id}")
    try:
        resolve_pincode(body.pincode)
    except LocationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    stream_id = uuid.uuid4().hex
    storage = _storage()
    principal.require_org(body.org_id)
    for key in body.photo_keys:
        if key.split("/", 1)[0] != body.org_id or "/" not in key:
            raise HTTPException(403, "photo belongs to a different organization")
        try:
            validate_image(storage.read_upload(key), key)
        except (FileNotFoundError, KeyError, ValueError) as exc:
            raise HTTPException(422, "photo is missing or invalid") from exc
    storage.create_stream(stream_id, {
        "org_id": body.org_id,
        "note": body.note,
        "quantity_kg": body.quantity_kg,
        "photo_keys": body.photo_keys,
        "pincode": body.pincode,
        "slider_w": 0.5,
        "status": "SUBMITTED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": principal.subject,
    })
    # No storage object is passed into the background task: a SQLite connection
    # created in this request's thread shouldn't be reused from the task's thread.
    # run_pipeline(storage=None) opens its own connection to the same local DB file.
    try:
        enqueue_pipeline(stream_id, background_tasks)
    except Exception:
        storage.update_stream(stream_id, status="FAILED", error="Could not start processing. Retry submission.")
        raise HTTPException(503, "could not start processing") from None
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


class RouteRequest(BaseModel):
    w: float = Field(default=0.5, ge=0, le=1, allow_inf_nan=False)
    evidence_weight: float = Field(default=0, ge=0, le=1, allow_inf_nan=False)
    item_index: int = Field(default=0, ge=0)


@app.put("/streams/{stream_id}/route")
def save_route(stream_id: str, body: RouteRequest, principal: Principal = Depends(get_principal)) -> dict:
    storage = _storage()
    stream = _get_stream_or_404(storage, stream_id)
    if stream["status"] not in ("ROUTED", "NEEDS_REVIEW"):
        raise HTTPException(409, "stream cannot change routing in its current state")
    items = (stream.get("characterization") or {}).get("items", [])
    if not 0 <= body.item_index < len(items):
        raise HTTPException(404, "no such item_index")
    events = ledger.item_events(storage.get_ledger_chain(stream_id), body.item_index, len(items))
    if any(e["event"] in ("handoff_matched", "handoff_collected", "handoff_weighed", "handoff_verified") for e in events):
        raise HTTPException(409, "routing is locked after handoff starts")
    result = get_route(stream_id, body.w, body.item_index, body.evidence_weight)
    _selected_processor(Item.model_validate(items[body.item_index]), result["routing"])
    routes, receipts = list(stream["routing"]), list(stream["receipts"])
    routes[body.item_index], receipts[body.item_index] = result["routing"], result["receipt"]
    ledger.append(storage, stream_id, "route_selected", {"item_index": body.item_index,
        "routing": result["routing"], "receipt": result["receipt"], "actor": principal.subject})
    storage.update_stream(stream_id, routing=routes, receipts=receipts)
    return result


class WipeRecordRequest(BaseModel):
    method: Literal["overwrite", "crypto_erase", "degauss", "physical_destruction"]
    certificate_ref: str = Field(min_length=1, max_length=200, pattern=r".*\S.*")
    operator: str = Field(min_length=1, max_length=200, pattern=r".*\S.*")
    item_index: int = Field(default=0, ge=0)


@app.post("/streams/{stream_id}/wipe")
def confirm_wipe(stream_id: str, body: WipeRecordRequest,
                 principal: Principal = Depends(get_principal)) -> WipeConfirmResponse:
    storage = _storage()
    stream = _get_stream_or_404(storage, stream_id)
    items = (stream.get("characterization") or {}).get("items", [])
    if not 0 <= body.item_index < len(items):
        raise HTTPException(404, "no such item_index")
    if not Item.model_validate(items[body.item_index]).is_storage_device:
        raise HTTPException(409, "item is not a storage device")
    ledger.record_wipe_confirmed(storage, stream_id, payload={**body.model_dump(),
        "actor": principal.subject, "note": ewaste.RECORD_NOTE}, item_index=body.item_index)
    return WipeConfirmResponse(ok=True)


@app.post("/streams/{stream_id}/draft-message")
def draft_pickup_message(stream_id: str, processor_id: str, item_index: int = 0,
                         principal: Principal = Depends(get_principal)) -> dict:
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

    if stream["status"] != "ROUTED":
        raise HTTPException(409, "human review must finish before requesting pickup")
    processor = _selected_processor(Item.model_validate(items[item_index]), stream["routing"][item_index], processor_id)

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
        "actor": principal.subject,
    })

    return {
        "draft_message": draft_message,
        "label": "Draft only. Not sent. A live version would send this through the buyer's account.",
        "sent": False,
    }


@app.get("/streams/{stream_id}/report")
def get_report(stream_id: str, format: Literal["pdf", "json"] = "pdf"):
    storage = _storage()
    stream = _get_stream_or_404(storage, stream_id)
    if format == "json":
        return {"stream_id": stream_id, "status": stream["status"], "receipts": stream.get("receipts")}
    filename = re.sub(r"[^A-Za-z0-9_-]", "_", stream_id)
    return Response(report.stream_pdf({"stream_id": stream_id, **stream}, ledger.verify(storage, stream_id)),
        media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="loopback-{filename}.pdf"'})


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
    decision: Literal["confirm_routing", "reclassify", "reject"]
    reviewer: str = Field(min_length=1, max_length=200)
    note: str = Field(default="", max_length=4000)
    material: str | None = None   # required for "reclassify"
    item_index: int = Field(default=0, ge=0)
    hazardous: bool = False
    is_storage_device: bool = False


@app.get("/review-queue")
def review_queue(org_id: str | None = None, principal: Principal = Depends(get_principal)) -> list[dict]:
    """Streams waiting on a person: NEEDS_REVIEW with no review decision yet."""
    storage = _storage()
    rows = []
    if org_id:
        principal.require_org(org_id)
    for oid in ([org_id] if org_id else principal.org_ids):
        for stream in storage.list_streams_by_org(oid):
            if stream.get("status") != "NEEDS_REVIEW":
                continue
            rows.append({
                "stream_id": stream["stream_id"], "org_id": oid,
                "assessments": stream.get("assessments") or [],
                "materials": [i["material"] for i in (stream.get("characterization") or {}).get("items", [])],
                "classifications": [{field: i[field] for field in ("material", "hazardous", "is_storage_device")}
                    for i in (stream.get("characterization") or {}).get("items", [])],
            })
    return rows


@app.post("/streams/{stream_id}/review")
def submit_review(stream_id: str, body: ReviewRequest, principal: Principal = Depends(get_principal)) -> dict:
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
    payload = {"reviewer": body.reviewer.strip(), "actor": principal.subject, "decision": body.decision, "note": body.note}

    if body.decision == "reject":
        new_status = "REJECTED"
    elif any(r and r.get("refused") for r in routings):
        raise HTTPException(status_code=409, detail="an item is out of scope; it can only be rejected")
    elif body.decision == "reclassify":
        valid = set(Item.model_fields["material"].annotation.__args__)
        if body.material not in valid:
            raise HTTPException(status_code=422, detail=f"material must be one of {sorted(valid)}")
        if not 0 <= body.item_index < len(items):
            raise HTTPException(404, "no such item_index")
        index = body.item_index
        previous_item = Item.model_validate(items[index])
        items[index] = previous_item.reclassified(body.material, hazardous=body.hazardous,
            is_storage_device=body.is_storage_device).model_dump()
        payload["material"] = body.material
        payload["item_index"] = index
        payload["previous_classification"] = {field: getattr(previous_item, field)
            for field in ("material", "hazardous", "is_storage_device")}
        payload["classification"] = {field: items[index][field]
            for field in ("material", "hazardous", "is_storage_device")}
        try:
            location = resolve_pincode(stream.get("pincode"))
        except LocationError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        item = Item.model_validate(items[index])
        previous = routings[index] or {}
        routing = find_processors(item, location, w=previous.get("slider_w", 0.5), evidence_weight=previous.get("evidence_weight", 0))
        routings[index] = routing
        receipts = [report.counterfactual_receipt(Item.model_validate(it), route).model_dump()
                    for it, route in zip(items, routings)]
        assessments = [assess_item(Item.model_validate(it)) for it in items]
        new_status = "NEEDS_REVIEW"  # reclassification is not an approval
    else:
        for i, r in enumerate(routings):
            _selected_processor(Item.model_validate(items[i]), r or {})
        if not items:
            raise HTTPException(409, "no item to confirm")

    ledger.append(storage, stream_id, event="human_review", payload=payload)
    review = {**payload, "at": datetime.now(timezone.utc).isoformat()}
    storage.update_stream(
        stream_id, status=new_status, review=review if new_status != "NEEDS_REVIEW" else None,
        review_history=[*(stream.get("review_history") or []), review],
        characterization={**stream["characterization"], "items": items},
        routing=routings, receipts=receipts, assessments=assessments,
    )
    return {"stream_id": stream_id, "status": new_status, "review": review}


class HandoffRequest(BaseModel):
    status: str
    weight_kg: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    processor_id: str | None = None
    item_index: int = Field(default=0, ge=0)


@app.post("/streams/{stream_id}/handoff")
def advance_handoff(stream_id: str, body: HandoffRequest, principal: Principal = Depends(get_principal)) -> dict:
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
    processor = _selected_processor(Item.model_validate(items[body.item_index]), routing, body.processor_id)
    processor_id = processor["id"]
    try:
        entry = ledger.record_handoff(
            storage, stream_id, processor_id, body.status, Item.model_validate(items[body.item_index]),
            payload={"actor": principal.subject, **({"weight_kg": body.weight_kg} if body.weight_kg is not None else {})},
            item_index=body.item_index,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"stream_id": stream_id, "status": body.status, "link_no": entry["link_no"]}


class DeviceRequest(BaseModel):
    asset_tag: str = Field(min_length=1, max_length=100, pattern=r".*\S.*")
    kind: Literal["laptop", "desktop", "server", "monitor", "phone", "network", "printer", "other"] = "other"
    condition: Literal["working", "repairable", "broken", "unknown"] = "unknown"
    storage_drives: int = Field(default=0, ge=0, le=64, strict=True)
    weight_kg: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    notes: str = Field(default="", max_length=4000)


class EwasteRegisterRequest(BaseModel):
    devices: list[DeviceRequest] = Field(min_length=1, max_length=100)


class DriveWipeRequest(WipeRecordRequest):
    pass


@app.post("/streams/{stream_id}/ewaste")
def register_ewaste(stream_id: str, body: EwasteRegisterRequest, principal: Principal = Depends(get_principal)) -> dict:
    """Records the devices in a retired-equipment batch. Each installed drive becomes its
    own tracked record. Returns the pathway per device (reuse, refurbish or recycle)."""
    storage = _storage()
    stream = _get_stream_or_404(storage, stream_id)
    try:
        batch = ewaste.register_devices(stream.get("ewaste"), [d.model_dump() for d in body.devices])
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    ledger.append(storage, stream_id, event="ewaste_devices_registered", payload={
        "asset_tags": [d["asset_tag"] for d in batch["devices"][-len(body.devices):]],
        "actor": principal.subject,
    })
    storage.update_stream(stream_id, ewaste=batch)
    return ewaste.summarize(batch)


@app.get("/streams/{stream_id}/ewaste")
def get_ewaste(stream_id: str) -> dict:
    return ewaste.summarize(_get_stream_or_404(_storage(), stream_id).get("ewaste"))


@app.post("/streams/{stream_id}/ewaste/drives/{drive_id}/wipe")
def wipe_drive(stream_id: str, drive_id: str, body: DriveWipeRequest, principal: Principal = Depends(get_principal)) -> dict:
    storage = _storage()
    stream = _get_stream_or_404(storage, stream_id)
    batch = stream.get("ewaste")
    if not batch:
        raise HTTPException(status_code=409, detail="no e-waste batch registered for this stream")
    try:
        ewaste.record_drive_wipe(storage, stream_id, batch, drive_id, body.method, body.certificate_ref, body.operator,
                                actor=principal.subject)
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
    storage = _storage()
    _get_stream_or_404(storage, chain_id)
    result = ledger.verify(storage, chain_id)
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
