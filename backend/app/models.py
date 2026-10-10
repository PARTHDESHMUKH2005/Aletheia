"""Pydantic schemas: Item, Characterization, and the request/response models for the API in section 2.

Item/Characterization pulled forward from Phase 1 because the Phase 0 hello_agent.py
acceptance check requires parsing vision output into a real Characterization model.
"""
from typing import Literal

from pydantic import BaseModel


class Item(BaseModel):
    material: Literal[
        "aluminium_scrap", "steel_scrap", "copper_scrap", "mixed_metal",
        "paper", "cardboard", "e_waste_computer", "e_waste_storage_drive",
        "e_waste_other", "battery_lead_acid", "battery_lithium",
        "used_oil", "other",
    ]
    composition_note: str
    quantity_kg: float | None
    quantity_basis: Literal["stated", "estimated"]
    purity: Literal["high", "mixed", "unknown"]
    hazardous: bool
    is_storage_device: bool
    confidence: float  # 0 to 1
    reasoning: str


class Characterization(BaseModel):
    items: list[Item]
    overall_confidence: float


StreamStatus = Literal["SUBMITTED", "CHARACTERIZING", "ROUTED", "NEEDS_REVIEW", "FAILED"]
HandoffStatus = Literal["requested", "matched", "collected", "weighed", "verified"]


# --- section 2 request/response shapes ---

class UploadRequest(BaseModel):
    count: int


class UploadTarget(BaseModel):
    key: str
    url: str


class StreamCreateRequest(BaseModel):
    org_id: str
    note: str = ""
    quantity_kg: float | None = None
    photo_keys: list[str]
    pincode: str | None = None  # feature spec section 1: location in, pincode or pin


class StreamCreateResponse(BaseModel):
    stream_id: str


class WipeConfirmResponse(BaseModel):
    ok: bool


class ProcessorPublic(BaseModel):
    id: str
    name: str
    location: dict
    tier: str
    accepted_materials: list[str]
    seeded: bool


class VerifyResponse(BaseModel):
    ok: bool
    links: int
    first_broken: int | None


# --- carbon-aware routing (feature spec section 2) ---

class ProcessorCandidate(BaseModel):
    processor_id: str
    name: str
    tier: str
    distance_km: float
    price_per_kg_inr: float
    recovery_rate: float          # seeded assumption, labelled as such
    net_rupees: float
    net_co2e_kg: float
    normalized_money: float       # 0 to 1
    normalized_carbon: float      # 0 to 1
    score: float                  # (1-w)*normalized_money + w*normalized_carbon
    authorized: bool
    review_required: bool


class RoutingDecision(BaseModel):
    slider_w: float               # 0 = max money, 1 = max carbon
    candidates: list[ProcessorCandidate]  # ranked, best first (scored candidates only)
    unscored_candidates: list[dict] = []  # eligible but missing price/CO2e data or not authorization-checked
    picked_processor_id: str | None
    explanation: str              # one-line trade-off explanation
    rule_name: str
    review_required: bool
    reuse_recommended_processor_id: str | None = None  # feature 6: reuse-before-recycle override
    recovery_rate_is_assumption: bool = True
    transport_factors_are_assumptions: bool = True


# --- counterfactual receipt (feature spec section 3) ---

class PriceRange(BaseModel):
    low_inr_per_kg: float
    high_inr_per_kg: float
    source: str
    as_of: str


class ReceiptCase(BaseModel):
    label: str                    # e.g. "landfill (default)" or "LoopBack routing"
    co2e_kg: float | None
    value_inr: float | None


class CounterfactualReceipt(BaseModel):
    material: str
    quantity_kg: float
    default_case: ReceiptCase
    chosen_case: ReceiptCase
    diff_rupees: float | None
    diff_co2e_kg: float | None
    price_range: PriceRange | None
    emission_factor_source: str | None
    emission_factor_label: str | None   # e.g. "US proxy, not India-specific"
    emission_factor_available: bool


# --- GET /streams/{id} ---

class StreamResponse(BaseModel):
    stream_id: str
    status: StreamStatus
    org_id: str
    characterization: Characterization | None = None
    routing: RoutingDecision | None = None
    receipt: CounterfactualReceipt | None = None
    ledger: list[dict] = []
    timings: dict = {}


class DashboardResponse(BaseModel):
    org_id: str
    kg_by_tier: dict[str, float]
    co2e_avoided_kg: float
    compliance_status: str
    disclaimer: str
