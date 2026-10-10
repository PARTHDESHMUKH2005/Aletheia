"""find_processors tool: carbon-aware routing with a money/carbon slider.

Formulas (feature spec section 2):
    net_rupees = price_per_kg * kg - transport_cost
    net_co2e   = avoided_kg_per_kg * kg * recovery_rate - transport_co2e
Distance is haversine between org and processor coordinates, computed in code,
not by the model. score = (1-w) * normalized_money + w * normalized_carbon,
w in [0, 1]. Calls lookup_rules internally (guardrail 1: routing can't skip rules).

Two constants below are assumptions, not sourced data, and are flagged as such:
TRANSPORT_COST_INR_PER_TONNE_KM and TRANSPORT_CO2E_KG_PER_TONNE_KM. They are
deliberately small so transport never dominates the much larger recycling
credit ("do not treat distance alone as the carbon driver").
"""
import json
import math
from pathlib import Path

from app.models import Item
from app.tools.guardrails import needs_review, processor_authorized_for
from app.tools.rules import lookup_rules

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_PROCESSORS: list[dict] = json.loads((_DATA_DIR / "processors.json").read_text())
_CO2_FACTORS: dict[str, dict] = {
    row["material"]: row for row in json.loads((_DATA_DIR / "co2.json").read_text())
}

TRANSPORT_COST_INR_PER_TONNE_KM = 3.0   # assumption, not sourced
TRANSPORT_CO2E_KG_PER_TONNE_KM = 0.062  # assumption, not sourced

_HIERARCHY_ORDER = {"reuse": 0, "refurbish": 1, "recycle": 2, "recovery": 3, "disposal": 4}

_WORKING_HINTS = ("working", "functional", "powers on", "good condition")
_BROKEN_HINTS = ("broken", "not working", "damaged", "non-functional", "dead", "cracked screen")


def haversine_km(a: dict, b: dict) -> float:
    if a.get("lat") is None or a.get("lng") is None or b.get("lat") is None or b.get("lng") is None:
        return 0.0
    radius_km = 6371.0
    lat1, lng1, lat2, lng2 = map(math.radians, [a["lat"], a["lng"], b["lat"], b["lng"]])
    dlat, dlng = lat2 - lat1, lng2 - lng1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * radius_km * math.asin(math.sqrt(h))


def _normalize(values: list[float]) -> list[float]:
    lo, hi = min(values), max(values)
    if hi == lo:
        return [1.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def _looks_reusable(item: Item) -> bool:
    if item.material not in ("e_waste_computer", "e_waste_other"):
        return False
    text = f"{item.composition_note} {item.reasoning}".lower()
    if any(hint in text for hint in _BROKEN_HINTS):
        return False
    return item.purity == "high" and any(hint in text for hint in _WORKING_HINTS)


def find_processors(item: Item, org_location: dict, w: float = 0.5, top_n: int = 3) -> dict:
    """Returns ranked, scored candidates plus any eligible-but-unscored ones, the
    pick, a one-line trade-off explanation, and the rule that governs this material.
    """
    if not 0.0 <= w <= 1.0:
        raise ValueError("w must be between 0 and 1")

    rule = lookup_rules(item.material, item.hazardous)
    review_required = needs_review(item, rule)
    quantity_kg = item.quantity_kg or 0.0
    tonne_km_factor = quantity_kg / 1000.0

    co2_row = _CO2_FACTORS.get(item.material)
    avoided_factor = co2_row["avoided_kg_co2e_per_kg"] if co2_row else None

    eligible = [p for p in _PROCESSORS if item.material in p["accepted_materials"]]

    scored: list[dict] = []
    unscored: list[dict] = []
    for p in eligible:
        authorized = processor_authorized_for(p, item.material, item.hazardous)
        distance_km = haversine_km(org_location, p["location"])
        transport_cost = TRANSPORT_COST_INR_PER_TONNE_KM * tonne_km_factor * distance_km
        transport_co2e = TRANSPORT_CO2E_KG_PER_TONNE_KM * tonne_km_factor * distance_km

        price = p.get("price_per_kg_inr")
        net_rupees = (price * quantity_kg - transport_cost) if price is not None else None

        net_co2e = None
        if avoided_factor is not None:
            net_co2e = avoided_factor * quantity_kg * p["recovery_rate"] - transport_co2e

        candidate = {
            "processor_id": p["id"],
            "name": p["name"],
            "tier": p["tier"],
            "distance_km": round(distance_km, 1),
            "price_per_kg_inr": price,
            "recovery_rate": p["recovery_rate"],
            "net_rupees": net_rupees,
            "net_co2e_kg": net_co2e,
            "authorized": authorized,
            "review_required": review_required,
        }
        if authorized and net_rupees is not None and net_co2e is not None:
            scored.append(candidate)
        else:
            reasons = []
            if not authorized:
                reasons.append("not authorization-checked")
            if price is None:
                reasons.append("no sourced price")
            if avoided_factor is None:
                reasons.append("no sourced CO2e factor")
            candidate["reason_unscored"] = ", ".join(reasons)
            unscored.append(candidate)

    if scored:
        norm_money = _normalize([c["net_rupees"] for c in scored])
        norm_carbon = _normalize([c["net_co2e_kg"] for c in scored])
        for c, nm, nc in zip(scored, norm_money, norm_carbon):
            c["normalized_money"] = nm
            c["normalized_carbon"] = nc
            c["score"] = (1 - w) * nm + w * nc
        scored.sort(key=lambda c: c["score"], reverse=True)

    ranked = scored[:top_n]
    picked = ranked[0] if ranked else None

    reuse_processor_id = None
    if _looks_reusable(item):
        reuse_candidates = [p for p in eligible if p["tier"] == "reuse"]
        if reuse_candidates:
            reuse_processor_id = reuse_candidates[0]["id"]

    if reuse_processor_id:
        explanation = (
            f"{item.material} looks reusable, so reuse/donation is recommended ahead of "
            f"recycling, per the waste hierarchy, regardless of the money/carbon slider."
        )
    elif picked:
        money_leader = max(scored, key=lambda c: c["normalized_money"])["processor_id"] if scored else None
        carbon_leader = max(scored, key=lambda c: c["normalized_carbon"])["processor_id"] if scored else None
        if money_leader == carbon_leader:
            explanation = f"{picked['name']} wins on both money and carbon at w={w}."
        elif picked["processor_id"] == money_leader:
            explanation = f"At w={w}, {picked['name']} is picked for money; a higher w would favor the carbon leader instead."
        else:
            explanation = f"At w={w}, {picked['name']} is picked for carbon avoided, trading off against the cheaper option."
    else:
        explanation = "No processor has both a sourced price and a sourced CO2e factor for this material yet; showing eligible options without a ranked pick."

    return {
        "slider_w": w,
        "candidates": ranked,
        "unscored_candidates": unscored,
        "picked_processor_id": picked["processor_id"] if picked else None,
        "explanation": explanation,
        "rule_name": rule["rule_name"],
        "review_required": review_required,
        "reuse_recommended_processor_id": reuse_processor_id,
    }
