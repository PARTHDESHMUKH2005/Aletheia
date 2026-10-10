"""generate_report tool: counterfactual receipt (feature spec section 3), kg by
tier, CO2e avoided, compliance status, PDF via ReportLab.

Never shows a single number as certain where the underlying data doesn't support
it: price comes as a low-high range with source and date; a missing CO2e factor
produces emission_factor_available=False rather than a fabricated number.
"""
import json
from pathlib import Path

from app.models import CounterfactualReceipt, Item, PriceRange, ReceiptCase

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CO2_FACTORS: dict[str, dict] = {
    row["material"]: row for row in json.loads((_DATA_DIR / "co2.json").read_text())
}
_PRICES: list[dict] = json.loads((_DATA_DIR / "prices.json").read_text())

_TIERS = ("reuse", "refurbish", "recycle", "recovery", "disposal")


def _price_range_for(material: str) -> PriceRange | None:
    rows = [r for r in _PRICES if r["material"] == material]
    if not rows:
        return None
    prices = [r["price_per_kg_inr"] for r in rows]
    # All current rows for a material share one source/date (same PDF); if that
    # changes, this just reports the first row's source rather than fabricating a blend.
    return PriceRange(
        low_inr_per_kg=min(prices),
        high_inr_per_kg=max(prices),
        source=rows[0]["source"],
        as_of=rows[0]["as_of"],
    )


def counterfactual_receipt(item: Item, routing_result: dict) -> CounterfactualReceipt:
    """Builds the default-case-vs-chosen-route receipt for one routed item.
    routing_result is find_processors()'s return dict.
    """
    quantity_kg = item.quantity_kg or 0.0
    co2_row = _CO2_FACTORS.get(item.material)
    factor_available = co2_row is not None and co2_row.get("avoided_kg_co2e_per_kg") is not None

    picked_id = routing_result.get("picked_processor_id")
    picked = next(
        (c for c in routing_result["candidates"] if c["processor_id"] == picked_id),
        None,
    )

    default_case = ReceiptCase(label="Landfill or informal buyer (default, no credit)", co2e_kg=0.0, value_inr=0.0)

    if picked is not None:
        chosen_case = ReceiptCase(
            label=f"LoopBack routing via {picked['name']}",
            co2e_kg=picked["net_co2e_kg"],
            value_inr=picked["net_rupees"],
        )
        diff_rupees = chosen_case.value_inr - default_case.value_inr
        diff_co2e = chosen_case.co2e_kg - default_case.co2e_kg
    else:
        chosen_case = ReceiptCase(label="No scored route yet (insufficient price/CO2e data)", co2e_kg=None, value_inr=None)
        diff_rupees = None
        diff_co2e = None

    return CounterfactualReceipt(
        material=item.material,
        quantity_kg=quantity_kg,
        default_case=default_case,
        chosen_case=chosen_case,
        diff_rupees=diff_rupees,
        diff_co2e_kg=diff_co2e,
        price_range=_price_range_for(item.material),
        emission_factor_source=co2_row["source"] if co2_row else None,
        emission_factor_label=co2_row["label"] if co2_row else None,
        emission_factor_available=factor_available,
    )


def dashboard_summary(routed_items: list[tuple[Item, dict]]) -> dict:
    """kg diverted by tier, total CO2e avoided, compliance status. routed_items is
    a list of (item, routing_result) pairs for one org's completed streams.
    """
    kg_by_tier = {tier: 0.0 for tier in _TIERS}
    co2e_avoided_kg = 0.0
    any_unverified_rule = False
    any_review = False

    for item, routing_result in routed_items:
        picked_id = routing_result.get("picked_processor_id")
        picked = next(
            (c for c in routing_result["candidates"] if c["processor_id"] == picked_id),
            None,
        )
        if picked is not None:
            kg_by_tier[picked["tier"]] = kg_by_tier.get(picked["tier"], 0.0) + (item.quantity_kg or 0.0)
            if picked["net_co2e_kg"] is not None:
                co2e_avoided_kg += picked["net_co2e_kg"]
        if routing_result.get("review_required"):
            any_review = True

    if any_review:
        compliance_status = "some items pending human review"
    else:
        compliance_status = "no items pending review"

    return {
        "kg_by_tier": kg_by_tier,
        "co2e_avoided_kg": round(co2e_avoided_kg, 2),
        "compliance_status": compliance_status,
        "disclaimer": "Routing aid only. Confirm rules and processor authorization with the official CPCB or State Board source.",
    }
