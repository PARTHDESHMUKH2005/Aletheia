"""find_processors tool: carbon-aware routing with a money/carbon slider.

Formulas (feature spec section 2), all per kg so the scale does not depend on quantity:
    net_rupees_per_kg = price_per_kg - transport_cost_per_kg
    net_co2e_per_kg   = avoided_kg_per_kg * recovery_rate - transport_co2e_per_kg
Distance is haversine between the pickup point and processor coordinates, computed
in code, not by the model. Missing or invalid coordinates raise; they are never
treated as zero distance. Calls lookup_rules internally (guardrail 1: routing can't
skip rules).

Scoring uses FIXED reference scales, not min-max over the shortlisted candidates:
    money_score  = net_rupees_per_kg / best net_rupees_per_kg
    carbon_score = net_co2e_per_kg   / best net_co2e_per_kg
where "best" is taken over ALL eligible, scoreable processors for the material
(including ones beyond the distance cap), so a score of 0.9 means "90% of the best
available option" whatever else happens to be on the shortlist. If the spread
between shortlisted candidates on a measure is under 2%, that measure is treated as
equal for all of them. score = (1-w)*money_score + w*carbon_score. Ties are broken
by nearer distance, then by name.

Assumptions, not sourced data: TRANSPORT_COST_INR_PER_TONNE_KM,
TRANSPORT_CO2E_KG_PER_TONNE_KM, every processor recovery_rate, and any price whose
price_basis is "illustrative_assumption". Transport is deliberately small so it
never dominates the much larger recycling credit.
"""
import json
import math
import os
from pathlib import Path

from app.models import Item
from app.tools.geo import validate_point
from app.tools.guardrails import authorization_label, needs_review, processor_authorized_for
from app.tools.report import get_avoided_factor
from app.tools.rules import lookup_rules, unverified_label

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_PROCESSORS: list[dict] = json.loads((_DATA_DIR / "processors.json").read_text())

# All scoring knobs live in data/scoring_config.json so they are visible and editable.
SCORING_CONFIG: dict = json.loads((_DATA_DIR / "scoring_config.json").read_text())

TRANSPORT_COST_INR_PER_TONNE_KM = SCORING_CONFIG["transport_cost_inr_per_tonne_km"]   # assumption, not sourced
TRANSPORT_CO2E_KG_PER_TONNE_KM = SCORING_CONFIG["transport_co2e_kg_per_tonne_km"]     # assumption, not sourced

DEFAULT_MAX_DISTANCE_KM = SCORING_CONFIG["default_max_distance_km"]   # ranking cap; override with MAX_DISTANCE_KM env var or the max_distance_km argument
EQUAL_SPREAD_THRESHOLD = SCORING_CONFIG["equal_spread_threshold"]     # spreads under this fraction on a measure count as equal
TIE_BREAK_RULE = "nearer distance first, then name (alphabetical)"

_HIERARCHY_ORDER = {"reuse": 0, "refurbish": 1, "recycle": 2, "recovery": 3, "disposal": 4}

_WORKING_HINTS = ("working", "functional", "powers on", "good condition")
_BROKEN_HINTS = ("broken", "not working", "damaged", "non-functional", "dead", "cracked screen")


def default_max_distance_km() -> float:
    raw = os.environ.get("MAX_DISTANCE_KM")
    if raw is None:
        return DEFAULT_MAX_DISTANCE_KM
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"MAX_DISTANCE_KM must be a number, got {raw!r}") from None
    if value <= 0:
        raise ValueError(f"MAX_DISTANCE_KM must be positive, got {raw!r}")
    return value


def haversine_km(a: dict, b: dict) -> float:
    """Great-circle distance in km. Raises InvalidCoordinatesError (a ValueError)
    if either point has missing, non-numeric, non-finite or out-of-range lat/lng.
    """
    lat1, lng1 = validate_point(a, "the pickup location")
    lat2, lng2 = validate_point(b, "the processor location")
    radius_km = 6371.0
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat, dlng = lat2 - lat1, lng2 - lng1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * radius_km * math.asin(math.sqrt(min(1.0, h)))


def _ratio_to_best(value: float, best: float) -> float:
    """value / best, floored at 0 and capped at 1. If the best is not positive
    there is nothing to scale by, so it is 1 for the best option and 0 otherwise.
    """
    if best > 0:
        return min(1.0, max(0.0, value / best))
    return 1.0 if value >= best else 0.0


def _is_equal_spread(values: list[float]) -> bool:
    if len(values) < 2:
        return True
    hi, lo = max(values), min(values)
    if hi == lo:
        return True
    if hi == 0:
        return False
    return (hi - lo) / abs(hi) < EQUAL_SPREAD_THRESHOLD


def _looks_reusable(item: Item) -> bool:
    if item.material not in ("e_waste_computer", "e_waste_other"):
        return False
    text = f"{item.composition_note} {item.reasoning}".lower()
    if any(hint in text for hint in _BROKEN_HINTS):
        return False
    return item.purity == "high" and any(hint in text for hint in _WORKING_HINTS)


def evidence_level(processor: dict) -> int:
    """0 = no authorization reference, 1 = reference on file but never checked,
    2 = reference plus a check date. A record of what is on file, not a verdict.
    """
    if not processor.get("authorization_ref"):
        return 0
    return 2 if processor.get("authorization_checked_on") else 1


def _why_not_picked(c: dict, pick: dict) -> str:
    """Plain-language reason a ranked option lost to the pick, from its own numbers."""
    parts = []
    d_money = c["net_rupees"] - pick["net_rupees"]
    d_carbon = c["net_co2e_kg"] - pick["net_co2e_kg"]
    if abs(d_money) >= 0.005:
        parts.append(f"INR {abs(d_money):.2f} {'more' if d_money > 0 else 'less'} net")
    if abs(d_carbon) >= 0.005:
        parts.append(f"{abs(d_carbon):.2f} kg CO2e {'more' if d_carbon > 0 else 'less'} avoided")
    d_km = c["distance_km"] - pick["distance_km"]
    if abs(d_km) >= 0.05:
        parts.append(f"{abs(d_km):.1f} km {'farther' if d_km > 0 else 'closer'}")
    if c["evidence_level"] != pick["evidence_level"]:
        parts.append("stronger authorization evidence on file" if c["evidence_level"] > pick["evidence_level"] else "weaker authorization evidence on file")
    if not parts:
        return "Same as the pick on every measure; placed lower by the tie-break rule."
    return "Compared with the pick: " + ", ".join(parts) + f". Score {c['score']:.3f} vs {pick['score']:.3f}."


def find_processors(
    item: Item, org_location: dict, w: float = 0.5, top_n: int = 3, max_distance_km: float | None = None,
    evidence_weight: float = 0.0,
) -> dict:
    """Returns ranked, scored candidates plus any eligible-but-unscored ones, the
    pick, a one-line trade-off explanation, and the rule that governs this material.
    Raises LocationError (InvalidCoordinatesError) on bad coordinates.
    """
    if not 0.0 <= w <= 1.0:
        raise ValueError("w must be between 0 and 1")
    if not 0.0 <= evidence_weight <= 1.0:
        raise ValueError("evidence_weight must be between 0 and 1")
    cap = default_max_distance_km() if max_distance_km is None else float(max_distance_km)

    rule = lookup_rules(item.material, item.hazardous)
    review_required = needs_review(item, rule)
    quantity_kg = item.quantity_kg or 0.0

    factor = get_avoided_factor(item.material)
    avoided_factor = factor["avoided_kg_co2e_per_kg"] if factor else None

    eligible = [p for p in _PROCESSORS if item.material in p["accepted_materials"]]
    if item.material.startswith("e_waste") and not _looks_reusable(item):
        # Reuse/donation is only offered for equipment that looks usable (waste hierarchy).
        eligible_for_ranking = [p for p in eligible if p["tier"] != "reuse"]
    else:
        eligible_for_ranking = eligible

    scoreable: list[dict] = []   # eligible with price, factor and authorization gate: define the reference scale
    unscored: list[dict] = []
    for p in eligible_for_ranking:
        gate_passed = processor_authorized_for(p, item.material, item.hazardous)
        distance_km = haversine_km(org_location, p["location"])
        transport_cost_pk = TRANSPORT_COST_INR_PER_TONNE_KM * distance_km / 1000.0
        transport_co2e_pk = TRANSPORT_CO2E_KG_PER_TONNE_KM * distance_km / 1000.0

        price = p.get("price_per_kg_inr")
        net_rupees_pk = (price - transport_cost_pk) if price is not None else None
        net_co2e_pk = (avoided_factor * p["recovery_rate"] - transport_co2e_pk) if avoided_factor is not None else None

        candidate = {
            "processor_id": p["id"],
            "name": p["name"],
            "tier": p["tier"],
            "pincode": p.get("pincode"),
            "distance_km": round(distance_km, 1),
            "price_per_kg_inr": price,
            "price_basis": p.get("price_basis"),
            "recovery_rate": p["recovery_rate"],
            "recovery_rate_basis": p.get("recovery_rate_basis", "illustrative_assumption"),
            "net_rupees_per_kg": net_rupees_pk,
            "net_co2e_per_kg": net_co2e_pk,
            "net_rupees": net_rupees_pk * quantity_kg if net_rupees_pk is not None else None,
            "net_co2e_kg": net_co2e_pk * quantity_kg if net_co2e_pk is not None else None,
            "gross_rupees": price * quantity_kg if price is not None else None,
            "transport_cost_rupees": transport_cost_pk * quantity_kg,
            "transport_co2e_kg": transport_co2e_pk * quantity_kg,
            "evidence_level": evidence_level(p),
            "authorization_gate_passed": gate_passed,
            "authorization_label": authorization_label(p),
            "review_required": review_required,
            "_distance_exact": distance_km,
        }
        if gate_passed and net_rupees_pk is not None and net_co2e_pk is not None:
            scoreable.append(candidate)
        else:
            reasons = []
            if not gate_passed:
                reasons.append("not authorization-checked")
            if price is None:
                reasons.append("no sourced price")
            if avoided_factor is None:
                reasons.append("no sourced CO2e factor")
            candidate["reason_unscored"] = ", ".join(reasons)
            unscored.append(candidate)

    # Fixed reference scale: best option among ALL scoreable processors for this material.
    best_money = max((c["net_rupees_per_kg"] for c in scoreable), default=None)
    best_carbon = max((c["net_co2e_per_kg"] for c in scoreable), default=None)

    in_range: list[dict] = []
    for c in scoreable:
        if c["_distance_exact"] > cap:
            c["reason_unscored"] = f"beyond max distance of {cap:g} km"
            unscored.append(c)
        else:
            in_range.append(c)

    money_equal = carbon_equal = False
    ranked: list[dict] = []
    tied_at_top = False
    if in_range:
        for c in in_range:
            c["money_score"] = _ratio_to_best(c["net_rupees_per_kg"], best_money)
            c["carbon_score"] = _ratio_to_best(c["net_co2e_per_kg"], best_carbon)
        money_equal = _is_equal_spread([c["net_rupees_per_kg"] for c in in_range])
        carbon_equal = _is_equal_spread([c["net_co2e_per_kg"] for c in in_range])
        top_money = max(c["money_score"] for c in in_range)
        top_carbon = max(c["carbon_score"] for c in in_range)
        for c in in_range:
            c["money_score_used"] = top_money if money_equal else c["money_score"]
            c["carbon_score_used"] = top_carbon if carbon_equal else c["carbon_score"]
            blended = (1 - w) * c["money_score_used"] + w * c["carbon_score_used"]
            c["evidence_score"] = c["evidence_level"] / 2
            c["score"] = (1 - evidence_weight) * blended + evidence_weight * c["evidence_score"]
        in_range.sort(key=lambda c: (-round(c["score"], 9), c["_distance_exact"], c["name"]))
        tied_at_top = len(in_range) > 1 and round(in_range[0]["score"], 9) == round(in_range[1]["score"], 9)
        ranked = in_range[:top_n]
        for c in ranked[1:]:
            c["why_not_picked"] = _why_not_picked(c, ranked[0])
        ranked[0]["why_not_picked"] = None

    for c in ranked + unscored:
        c.pop("_distance_exact", None)
    for c in in_range[top_n:]:
        c.pop("_distance_exact", None)

    picked = ranked[0] if ranked else None

    reuse_processor_id = None
    if _looks_reusable(item):
        reuse_candidates = [p for p in eligible if p["tier"] == "reuse"]
        if reuse_candidates:
            reuse_processor_id = reuse_candidates[0]["id"]

    equal_notes = [m for m, eq in (("money", money_equal), ("carbon", carbon_equal)) if eq and len(in_range) > 1]
    equal_note = f" Differences under 2% on {' and '.join(equal_notes)} were treated as equal." if equal_notes else ""

    if reuse_processor_id:
        explanation = (
            f"{item.material} looks reusable, so reuse/donation is recommended ahead of "
            f"recycling, per the waste hierarchy, regardless of the money/carbon slider."
        )
    elif picked and tied_at_top:
        explanation = (
            f"At w={w}, {picked['name']} tied on score with another option; tie broken by "
            f"{TIE_BREAK_RULE}.{equal_note}"
        )
    elif picked:
        money_leaders = {c["processor_id"] for c in ranked if c["money_score_used"] == max(x["money_score_used"] for x in ranked)}
        carbon_leaders = {c["processor_id"] for c in ranked if c["carbon_score_used"] == max(x["carbon_score_used"] for x in ranked)}
        pid = picked["processor_id"]
        if pid in money_leaders and pid in carbon_leaders:
            explanation = f"{picked['name']} wins on both money and carbon at w={w}."
        elif pid in money_leaders:
            explanation = f"At w={w}, {picked['name']} is picked for money; a higher w would favor the carbon leader instead."
        else:
            explanation = f"At w={w}, {picked['name']} is picked for carbon avoided, trading off against the cheaper option."
        explanation += equal_note
    elif scoreable:
        explanation = f"No processor with a price and CO2e factor for this material is within {cap:g} km, so there is no ranked pick."
    else:
        explanation = "No processor has both a sourced price and a sourced CO2e factor for this material yet; showing eligible options without a ranked pick."

    return {
        "slider_w": w,
        "evidence_weight": evidence_weight,
        "max_distance_km": cap,
        "candidates": ranked,
        "unscored_candidates": unscored,
        "picked_processor_id": picked["processor_id"] if picked else None,
        "explanation": explanation,
        "tie_break_rule": TIE_BREAK_RULE,
        "reference_scale": {"best_net_rupees_per_kg": best_money, "best_net_co2e_per_kg": best_carbon},
        "measures_treated_equal": {"money": money_equal and len(in_range) > 1, "carbon": carbon_equal and len(in_range) > 1},
        "rule_name": rule["rule_name"],
        "compliance": {
            "rule_name": rule["rule_name"],
            "section_ref": rule.get("section_ref"),
            "handler_requirement": rule["handler_requirement"],
            "paperwork": rule["paperwork"],
            "key_requirements": rule.get("key_requirements", []),
            "hazardous": rule.get("hazardous", False) or bool(item.hazardous),
            "regulated": rule.get("regulated", False),
            "verified": rule["verified"],
            "unverified_label": unverified_label(rule),
        },
        "review_required": review_required,
        "reuse_recommended_processor_id": reuse_processor_id,
    }
