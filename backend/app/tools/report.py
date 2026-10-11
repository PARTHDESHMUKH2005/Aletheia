"""generate_report tool: counterfactual receipt (feature spec section 3), kg by
tier, CO2e avoided, compliance status, PDF via ReportLab.

Never shows a single number as certain where the underlying data doesn't support
it: price comes as a low-high range with source and date; a missing CO2e factor
produces emission_factor_available=False rather than a fabricated number.
"""
import json
from pathlib import Path

from app.models import CounterfactualReceipt, Item, PriceRange, ReceiptCase
from app.tools.ledger import HANDOFF_ORDER

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_EMISSION_DATA: dict = json.loads((_DATA_DIR / "emission_factors.json").read_text())
_EMISSION_FACTORS: dict[str, dict] = {row["material"]: row for row in _EMISSION_DATA["factors"]}
_EMISSION_PROXY_LABEL: str = _EMISSION_DATA["_meta"]["label"]
_PRICES: list[dict] = json.loads((_DATA_DIR / "prices.json").read_text())

_TIERS = ("reuse", "refurbish", "recycle", "recovery", "disposal")


def get_avoided_factor(material: str) -> dict | None:
    """Normalized view of one material's emission_factors.json row: avoided_kg_co2e_per_kg,
    source, label, verified. None if no row or no avoided_kg_per_kg value exists.
    Shared by matching.py so both tools read the exact same source of truth.
    """
    row = _EMISSION_FACTORS.get(material)
    if row is None or row.get("avoided_kg_per_kg") is None:
        return None
    return {
        "avoided_kg_co2e_per_kg": row["avoided_kg_per_kg"],
        "source": row["source"],
        "label": _EMISSION_PROXY_LABEL if row.get("verified") else "unverified estimate, not a WARM citation",
        "verified": bool(row.get("verified")),
    }


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
    quantity_kg = item.quantity_kg
    factor = get_avoided_factor(item.material)

    picked_id = routing_result.get("reuse_recommended_processor_id") or routing_result.get("picked_processor_id")
    picked = next(
        (c for c in routing_result.get("candidates", []) if c["processor_id"] == picked_id),
        None,
    )

    default_case = ReceiptCase(label="Landfill or informal buyer (default, no credit)", co2e_kg=0.0, value_inr=0.0)

    if quantity_kg is None:
        chosen_case = ReceiptCase(label="Enter a weight to calculate money and CO2e credit", co2e_kg=None, value_inr=None)
        diff_rupees = diff_co2e = None
    elif picked is not None:
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
        warning="Weight is unknown. Totals exclude this item until a weight is recorded." if quantity_kg is None else None,
        default_case=default_case,
        chosen_case=chosen_case,
        diff_rupees=diff_rupees,
        diff_co2e_kg=diff_co2e,
        price_range=_price_range_for(item.material),
        emission_factor_source=factor["source"] if factor else None,
        emission_factor_label=factor["label"] if factor else None,
        emission_factor_available=factor is not None,
    )


def dashboard_summary(routed_items: list[tuple[Item, dict]]) -> dict:
    """kg diverted by tier, total CO2e avoided, compliance status. routed_items is
    a list of (item, routing_result) pairs for one org's completed streams.
    """
    kg_by_tier = {tier: 0.0 for tier in _TIERS}
    co2e_avoided_kg = 0.0
    any_review = False

    for item, routing_result in routed_items:
        picked_id = routing_result.get("reuse_recommended_processor_id") or routing_result.get("picked_processor_id")
        picked = next(
            (c for c in routing_result.get("candidates", []) if c["processor_id"] == picked_id),
            None,
        )
        if picked is not None:
            kg_by_tier[picked["tier"]] = kg_by_tier.get(picked["tier"], 0.0) + (item.quantity_kg or 0.0)
            if picked["net_co2e_kg"] is not None:
                co2e_avoided_kg += picked["net_co2e_kg"]
        elif routing_result.get("reuse_recommended_processor_id"):
            kg_by_tier["reuse"] += item.quantity_kg or 0.0
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


# --- organization impact dashboard ---

_HANDOFF_ORDER = HANDOFF_ORDER
_PAPERWORK_EVENTS = {  # paperwork LoopBack can check from the ledger
    "data wipe certificate": "data_wipe_confirmed",
    "transfer record": "handoff_collected",
    "weighment slip": "handoff_weighed",
    "ledger record": None,  # exists as soon as the stream has any ledger entry
}
_METHODOLOGY = {
    "co2e": "Net CO2e = (avoided kg CO2e per kg for the material x the buyer's recovery rate - transport CO2e) x kg. "
            "Factors are US EPA WARM values used as a proxy, not India-specific; see factors_used for each.",
    "revenue": "Gross = buyer price per kg x kg. Transport = INR per tonne-km x straight-line km x kg. Net = gross - transport. "
               "Prices marked illustrative are placeholders, not quotes.",
    "projected_vs_realised": "Projected counts every routed item at its stated weight. Realised counts only items whose "
                             "handoff reached 'verified', at the weight recorded then if one was entered.",
}


def _handoff_state(events: list[dict]) -> tuple[str | None, float | None]:
    """Furthest handoff status reached and the weight recorded with it, from ledger entries."""
    import json as _json
    best, weight = -1, None
    for e in events:
        if not e["event"].startswith("handoff_"):
            continue
        status = e["event"][len("handoff_"):]
        if status in _HANDOFF_ORDER:
            idx = _HANDOFF_ORDER.index(status)
            if idx > best:
                best = idx
                payload = _json.loads(e["payload_json"])
                if payload.get("weight_kg") is not None:
                    weight = float(payload["weight_kg"])
    return (_HANDOFF_ORDER[best] if best >= 0 else None), weight


def _gross_and_transport(picked: dict, kg: float) -> tuple[float, float]:
    """Gross and transport rupees for a picked buyer. Streams saved before these fields
    existed are rebuilt from the stored price and net, so net always equals gross - transport."""
    gross = picked.get("gross_rupees")
    if gross is None:
        price = picked.get("price_per_kg_inr")
        gross = price * kg if price is not None else (picked.get("net_rupees") or 0.0)
    transport = picked.get("transport_cost_rupees")
    if transport is None:
        transport = gross - (picked.get("net_rupees") or 0.0)
    return gross, transport


def org_impact(streams: list[dict], ledgers: dict[str, list[dict]]) -> dict:
    """Operational dashboard for one organization.

    streams: stored stream dicts (with stream_id); ledgers: stream_id -> ledger entries.
    Items still waiting on a human (NEEDS_REVIEW) are listed as pending and kept out of
    the projected and realised totals.
    """
    from app.tools.rules import lookup_rules

    submitted_kg = collected_kg = verified_kg = 0.0
    kg_by_tier = {tier: 0.0 for tier in _TIERS}
    proj = {"gross_inr": 0.0, "transport_cost_inr": 0.0, "net_inr": 0.0, "co2e_kg": 0.0}
    real = {"gross_inr": 0.0, "transport_cost_inr": 0.0, "net_inr": 0.0, "co2e_kg": 0.0}
    factors_used: dict[str, dict] = {}
    no_factor_materials: set[str] = set()
    awaiting_review = awaiting_pickup = awaiting_verification = 0
    actions: list[dict] = []
    missing_docs: list[dict] = []
    untracked: set[str] = set()
    counted = 0

    for stream in sorted(streams, key=lambda s: s["stream_id"]):
        sid, status = stream["stream_id"], stream.get("status")
        characterization = stream.get("characterization")
        if status == "FAILED" or not characterization:
            continue
        events = ledgers.get(sid, [])
        routings = stream.get("routing") or []
        reviewed = status == "ROUTED" and bool(stream.get("review"))

        if status == "NEEDS_REVIEW" and not reviewed:
            awaiting_review += 1
            actions.append({"stream_id": sid, "action": "Human review needed", "detail": "Open the review queue."})
        if status == "REJECTED":
            continue

        batch = stream.get("ewaste")
        if batch:
            for reason in blocking_reasons_ewaste(batch):
                actions.append({"stream_id": sid, "action": "Record data wipe", "detail": reason})

        for idx, (item_data, routing) in enumerate(zip(characterization["items"], routings)):
            from app.tools.ledger import item_events
            scoped_events = item_events(events, idx, len(characterization["items"]))
            event_names = {e["event"] for e in scoped_events}
            handoff, handoff_weight = _handoff_state(scoped_events)
            item = Item.model_validate(item_data)
            kg = item.quantity_kg or 0.0
            submitted_kg += kg
            if not item.quantity_kg:
                actions.append({"stream_id": sid, "action": "Enter a weight", "detail": f"{item.material} has no usable weight, so totals count it as 0 kg."})
            if not routing or routing.get("refused"):
                actions.append({"stream_id": sid, "action": "Out of scope", "detail": f"{item.material} was refused and needs a different route."})
                continue
            if status == "NEEDS_REVIEW" and not reviewed:
                continue

            rule = lookup_rules(item.material, item.hazardous)
            for paper in rule["paperwork"]:
                if paper not in _PAPERWORK_EVENTS:
                    untracked.add(paper)
                    continue
                needed_event = _PAPERWORK_EVENTS[paper]
                if needed_event is None:
                    present = bool(scoped_events)
                    due = True
                elif needed_event in ("handoff_collected", "handoff_weighed"):
                    present = needed_event in event_names
                    # only chase it once the handoff has moved past that step
                    due = handoff in (("weighed", "verified") if needed_event == "handoff_collected" else ("verified",))
                else:
                    present = needed_event in event_names or bool(batch and batch.get("drives") and not blocking_reasons_ewaste(batch))
                    due = item.is_storage_device or item.material == "e_waste_storage_drive"
                if due and not present:
                    missing_docs.append({"stream_id": sid, "document": paper, "material": item.material})
            counted += 1

            reuse_id = routing.get("reuse_recommended_processor_id")
            selected_id = reuse_id or routing.get("picked_processor_id")
            picked = next((c for c in routing["candidates"] if c["processor_id"] == selected_id), None)
            if picked is None and not reuse_id:
                actions.append({"stream_id": sid, "action": "No route", "detail": f"No buyer cleared the checks for {item.material}."})
                continue
            if picked is None:
                kg_by_tier["reuse"] += kg
            else:
                kg_by_tier[picked["tier"]] = kg_by_tier.get(picked["tier"], 0.0) + kg
                gross, transport = _gross_and_transport(picked, kg)
                co2 = picked.get("net_co2e_kg")
                proj["gross_inr"] += gross
                proj["transport_cost_inr"] += transport
                proj["net_inr"] += picked["net_rupees"] or 0.0
                if co2 is not None:
                    proj["co2e_kg"] += co2
                factor = get_avoided_factor(item.material)
                if factor:
                    factors_used[item.material] = {"kg_co2e_per_kg": factor["avoided_kg_co2e_per_kg"], "source": factor["source"], "label": factor["label"], "verified": factor["verified"]}
                else:
                    no_factor_materials.add(item.material)

            if handoff is None:
                actions.append({"stream_id": sid, "action": "Request pickup", "detail": f"{item.material} is routed but no pickup was requested."})
            elif handoff in ("requested", "matched"):
                awaiting_pickup += 1
            elif handoff in ("collected", "weighed"):
                awaiting_verification += 1
                collected_kg += handoff_weight if handoff_weight is not None else kg
            elif handoff == "verified":
                actual = handoff_weight if handoff_weight is not None else kg
                collected_kg += actual
                verified_kg += actual
                if picked is not None and kg > 0:
                    scale = actual / kg
                    gross_v, transport_v = _gross_and_transport(picked, kg)
                    real["gross_inr"] += gross_v * scale
                    real["transport_cost_inr"] += transport_v * scale
                    real["net_inr"] += (picked["net_rupees"] or 0.0) * scale
                    real["co2e_kg"] += (picked["net_co2e_kg"] or 0.0) * scale
                elif picked is not None and actual > 0:
                    gross_v = (picked.get("price_per_kg_inr") or 0) * actual
                    net_v = (picked.get("net_rupees_per_kg") or 0) * actual
                    real["gross_inr"] += gross_v
                    real["transport_cost_inr"] += gross_v - net_v
                    real["net_inr"] += net_v
                    real["co2e_kg"] += (picked.get("net_co2e_per_kg") or 0) * actual

    def _round(d):
        return {k: round(v, 2) for k, v in d.items()}

    return {
        "items_counted": counted,
        "kg": {"submitted": round(submitted_kg, 2), "collected": round(collected_kg, 2), "verified": round(verified_kg, 2)},
        "kg_by_tier": {k: round(v, 2) for k, v in kg_by_tier.items()},
        "revenue_inr": {"projected": _round(proj), "realised": _round(real)},
        "co2e": {
            "projected_kg": round(proj["co2e_kg"], 2),
            "realised_kg": round(real["co2e_kg"], 2),
            "factors_used": factors_used,
            "materials_without_factor": sorted(no_factor_materials),
            "methodology": _METHODOLOGY["co2e"],
        },
        "pending": {"awaiting_review": awaiting_review, "awaiting_pickup": awaiting_pickup, "awaiting_verification": awaiting_verification},
        "outstanding_actions": actions,
        "missing_documents": missing_docs,
        "paperwork_not_tracked_by_loopback": sorted(untracked),
        "methodology": _METHODOLOGY,
        "disclaimer": "Routing aid only. Buyers, most prices and recovery rates are demo data. Confirm rules and processor authorization with the official CPCB or State Board source.",
    }


def blocking_reasons_ewaste(batch: dict) -> list[str]:
    from app.tools.ewaste import blocking_reasons
    return blocking_reasons(batch)


def stream_pdf(stream: dict, verification: dict) -> bytes:
    """Downloadable receipt with data provenance and ledger status, built in memory."""
    from io import BytesIO
    from xml.sax.saxutils import escape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    output = BytesIO()
    styles = getSampleStyleSheet()
    def paragraph(text, style="BodyText"):
        return Paragraph(escape(str(text)), styles[style])
    story = [paragraph("LoopBack Waste Passport", "Title"),
             paragraph(f"Record: {stream['stream_id']}"),
             paragraph(f"Organization: {stream['org_id']} | Status: {stream['status']}"),
             paragraph("Demo data. Buyers, most prices and recovery rates are illustrative. No pickup is sent."),
             Spacer(1, 14)]
    items = (stream.get("characterization") or {}).get("items", [])
    receipts = stream.get("receipts") or []
    routes = stream.get("routing") or []
    for index, data in enumerate(items):
        story.append(paragraph(f"Item {index + 1}: {data['material'].replace('_', ' ')}", "Heading2"))
        receipt = receipts[index] if index < len(receipts) else None
        routing = routes[index] if index < len(routes) else None
        story.append(paragraph(f"Weight: {data.get('quantity_kg')} kg ({data['quantity_basis']}). "
            f"Confidence: {data['confidence']} (model self-reported, not calibrated)."))
        if routing:
            story.append(paragraph(routing.get("explanation", "Out of scope; human review required.")))
        if receipt:
            if receipt.get("warning"):
                story.append(paragraph(receipt["warning"]))
            values = [["Case", "Value (INR)", "CO2e credit (kg)"]]
            for key in ("default_case", "chosen_case"):
                case = receipt[key]
                values.append([paragraph(case["label"]),
                    "Unavailable" if case["value_inr"] is None else f"{case['value_inr']:.2f}",
                    "Unavailable" if case["co2e_kg"] is None else f"{case['co2e_kg']:.2f}"])
            table = Table(values, colWidths=[280, 100, 120])
            table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story.extend([Spacer(1, 8), table,
                paragraph(f"Emission factor: {receipt.get('emission_factor_source') or 'Unavailable'}. "
                          f"{receipt.get('emission_factor_label') or ''}")])
            if receipt.get("price_range"):
                price = receipt["price_range"]
                story.append(paragraph(f"Price benchmark: INR {price['low_inr_per_kg']} to "
                    f"{price['high_inr_per_kg']}/kg. {price['source']}; {price['as_of']}."))
        story.append(Spacer(1, 12))
    status = "Hash chain verified" if verification["ok"] else "Hash chain unverified, empty, legacy or damaged"
    story.extend([paragraph(f"Ledger: {status}; {verification['links']} links.", "Heading2"),
        paragraph("Hash verification checks recorded contents. It does not certify a real handoff or prevent a database owner from replacing the whole chain."),
        paragraph("Routing aid only. Confirm rules and processor authorization with official CPCB or State Board sources.")])
    SimpleDocTemplate(output, title="LoopBack Waste Passport", leftMargin=40, rightMargin=40).build(story)
    return output.getvalue()
