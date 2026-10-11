"""Pydantic schemas: Item, Characterization, and the request/response models for the API in section 2.

Item/Characterization pulled forward from Phase 1 because the Phase 0 hello_agent.py
acceptance check requires parsing vision output into a real Characterization model.
"""
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from app.uploads import MAX_PHOTOS, validate_upload_key


class Item(BaseModel):
    material: Literal[
        "aluminium_scrap", "steel_scrap", "copper_scrap", "mixed_metal",
        "paper", "cardboard", "e_waste_computer", "e_waste_storage_drive",
        "e_waste_other", "battery_lead_acid", "battery_lithium",
        "used_oil", "other",
    ]
    composition_note: str
    quantity_kg: float | None = Field(gt=0, allow_inf_nan=False)
    quantity_basis: Literal["stated", "estimated"]
    purity: Literal["high", "mixed", "unknown"]
    hazardous: bool
    is_storage_device: bool
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)  # self-reported, not calibrated
    reasoning: str
    # Visible contaminants the model names (for example "steel pieces mixed in", "oil stains").
    # Plain strings, no percentages: a purity figure is not shown because nothing validates one.
    contaminants: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def enforce_material_flags(self):
        if self.material in ("battery_lead_acid", "battery_lithium", "used_oil"):
            self.hazardous = True
        if self.material == "e_waste_storage_drive":
            self.is_storage_device = True
        return self

    def reclassified(self, material: str, *, hazardous: bool = False, is_storage_device: bool = False):
        """Reviewer correction replaces classification flags; required flags still apply.

        The original model flags remain valid for ordinary characterization, including
        hazardous contamination or installed storage in an otherwise reusable item.
        """
        return Item.model_validate({**self.model_dump(), "material": material,
            "hazardous": hazardous, "is_storage_device": is_storage_device})


class Characterization(BaseModel):
    items: list[Item]
    overall_confidence: float = Field(ge=0, le=1, allow_inf_nan=False)


StreamStatus = Literal["SUBMITTED", "CHARACTERIZING", "ROUTED", "NEEDS_REVIEW", "REJECTED", "FAILED"]
HandoffStatus = Literal["requested", "matched", "collected", "weighed", "verified"]


# --- section 2 request/response shapes ---

class UploadRequest(BaseModel):
    count: int = Field(ge=1, le=MAX_PHOTOS)
    org_id: str
    sizes: list[int] | None = None

    @model_validator(mode="after")
    def upload_sizes(self):
        from app.uploads import MAX_UPLOAD_BYTES
        if self.sizes is not None and (len(self.sizes) != self.count or
                any(not 0 < size <= MAX_UPLOAD_BYTES for size in self.sizes)):
            raise ValueError("provide one size between 1 byte and 5 MiB per photo")
        return self


class UploadTarget(BaseModel):
    key: str
    url: str


class StreamCreateRequest(BaseModel):
    org_id: str
    note: str = Field(default="", max_length=4000)
    quantity_kg: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    photo_keys: list[str] = Field(min_length=1, max_length=MAX_PHOTOS)
    pincode: str | None = None  # feature spec section 1: location in, pincode or pin

    @field_validator("photo_keys")
    @classmethod
    def safe_photo_keys(cls, keys):
        for key in keys:
            validate_upload_key(key)
        if len(set(keys)) != len(keys):
            raise ValueError("photo keys must be distinct")
        return keys


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
    pincode: str | None = None
    distance_km: float
    price_per_kg_inr: float | None
    price_basis: str | None       # "sourced" | "illustrative_assumption" | None (no price)
    recovery_rate: float          # illustrative assumption, labelled as such
    recovery_rate_basis: str = "illustrative_assumption"
    net_rupees_per_kg: float
    net_co2e_per_kg: float
    net_rupees: float
    net_co2e_kg: float
    money_score: float            # net_rupees_per_kg / best across all eligible processors (raw, 0 to 1)
    carbon_score: float           # net_co2e_per_kg / best across all eligible processors (raw, 0 to 1)
    money_score_used: float       # equals money_score unless the money spread was under 2%
    carbon_score_used: float
    score: float                  # (1-w)*money_score_used + w*carbon_score_used
    authorization_gate_passed: bool   # accepts the material and clears the hazardous-item gate; NOT a statement that it is authorized
    authorization_label: str          # "demo only, authorization not checked" when no authorization_ref
    review_required: bool
    gross_rupees: float | None = None
    transport_cost_rupees: float = 0.0
    transport_co2e_kg: float = 0.0
    evidence_level: int = 0       # 0 none, 1 reference unchecked, 2 reference with check date
    evidence_score: float = 0.0
    why_not_picked: str | None = None


class RoutingDecision(BaseModel):
    slider_w: float               # 0 = max money, 1 = max carbon
    evidence_weight: float = 0.0  # share of the score given to authorization evidence on file
    candidates: list[ProcessorCandidate]  # ranked, best first (scored candidates only)
    unscored_candidates: list[dict] = []  # eligible but missing price/CO2e data or not authorization-checked
    picked_processor_id: str | None
    explanation: str              # one-line trade-off explanation
    max_distance_km: float = 500.0
    tie_break_rule: str = ""
    reference_scale: dict = {}
    measures_treated_equal: dict = {}
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
    quantity_kg: float | None
    warning: str | None = None
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
    routing: list[dict] | None = None
    receipts: list[CounterfactualReceipt | None] | None = None
    ledger: list[dict] = []
    timings: dict = {}


class DashboardResponse(BaseModel):
    org_id: str
    kg_by_tier: dict[str, float]
    co2e_avoided_kg: float
    compliance_status: str
    disclaimer: str
