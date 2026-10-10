"""Per-item quality assessment: confidence band, visible contamination, and whether a
human must look before anything moves. Built only from what the model returned and
from fixed rules in code.

Deliberately NOT here: a purity percentage. The model only says high / mixed / unknown,
and no evaluation in this repo validates a numeric purity, so none is shown.

The confidence number is the model's own score. It is reported as "model self-reported,
not calibrated" until an evaluation run (eval/run_eval.py) supports a stronger claim.
"""
from app.models import Item
from app.tools.guardrails import (
    _ALWAYS_REVIEW_MATERIALS,
    _CLEAN_METAL_MATERIALS,
    _CONTAMINATION_KEYWORDS,
    out_of_scope_flag,
)

LOW_CONFIDENCE_THRESHOLD = 0.7
HAZARDOUS_CONFIDENCE_THRESHOLD = 0.85
HIGH_CONFIDENCE_THRESHOLD = 0.85

CONFIDENCE_BASIS = "model self-reported score, not calibrated against labelled outcomes"


def confidence_band(confidence: float) -> str:
    if confidence >= HIGH_CONFIDENCE_THRESHOLD:
        return "high"
    if confidence >= LOW_CONFIDENCE_THRESHOLD:
        return "medium"
    return "low"


def detected_contaminants(item: Item) -> list[str]:
    """Model-named contaminants plus keyword hits in its description (deduplicated)."""
    found = [c.strip() for c in item.contaminants if c.strip()]
    text = f"{item.composition_note} {item.reasoning}".lower()
    for keyword in _CONTAMINATION_KEYWORDS:
        if keyword in text and not any(keyword in c.lower() for c in found):
            found.append(f"mentions '{keyword}'")
    return found


def assess_item(item: Item) -> dict:
    scope = out_of_scope_flag(item)
    threshold = HAZARDOUS_CONFIDENCE_THRESHOLD if item.hazardous else LOW_CONFIDENCE_THRESHOLD
    contaminants = detected_contaminants(item)

    review_reasons: list[str] = []
    if scope:
        review_reasons.append(f"out of LoopBack scope ({scope})")
    if item.confidence < threshold:
        review_reasons.append(f"confidence {item.confidence:.2f} is below the {threshold:.2f} needed for this item")
    if item.hazardous:
        review_reasons.append("hazardous item")
    if item.material in _ALWAYS_REVIEW_MATERIALS:
        review_reasons.append(f"{item.material} always goes to a person")
    if item.material == "other":
        review_reasons.append("material could not be identified")

    inspection_reasons: list[str] = []
    if item.material in _CLEAN_METAL_MATERIALS:
        if item.purity == "mixed":
            inspection_reasons.append("model reports mixed material")
        if contaminants:
            inspection_reasons.append("visible contamination: " + "; ".join(contaminants))
    if item.quantity_kg is None or item.quantity_kg <= 0:
        inspection_reasons.append("no usable weight")
    elif item.quantity_basis == "estimated":
        inspection_reasons.append("weight is an estimate")

    if scope:
        action = "Do not route. Out of scope; refer to the proper authority."
    elif review_reasons:
        action = "Send to a human reviewer before anything moves."
    elif any(r != "weight is an estimate" for r in inspection_reasons):
        action = "Manual inspection before confirming the price."
    elif inspection_reasons:
        action = "Weigh on pickup to confirm the price."
    else:
        action = "No extra check needed beyond normal weighing."

    return {
        "material": item.material,
        "confidence": item.confidence,
        "confidence_band": confidence_band(item.confidence),
        "confidence_basis": CONFIDENCE_BASIS,
        "purity": item.purity,
        "purity_note": "Category only (high / mixed / unknown). No percentage is shown because none is validated.",
        "contaminants": contaminants,
        "needs_human_review": bool(review_reasons),
        "review_reasons": review_reasons,
        "inspection_reasons": inspection_reasons,
        "price_is_provisional": bool(inspection_reasons),
        "recommended_action": action,
    }
