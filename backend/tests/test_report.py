from app.models import Item
from app.tools import report


def make_item(**overrides) -> Item:
    defaults = dict(
        material="steel_scrap", composition_note="clean steel can", quantity_kg=100.0,
        quantity_basis="estimated", purity="high", hazardous=False,
        is_storage_device=False, confidence=0.9, reasoning="clean",
    )
    defaults.update(overrides)
    return Item(**defaults)


FAKE_ROUTING_WITH_PICK = {
    "slider_w": 0.5,
    "candidates": [{
        "processor_id": "proc1", "name": "Demo Foundry", "tier": "recycle",
        "distance_km": 10.0, "price_per_kg_inr": 32.8, "recovery_rate": 0.8,
        "net_rupees": 3270.0, "net_co2e_kg": 140.0,
        "normalized_money": 1.0, "normalized_carbon": 1.0, "score": 1.0,
        "authorized": True, "review_required": False,
    }],
    "unscored_candidates": [],
    "picked_processor_id": "proc1",
    "explanation": "test",
    "rule_name": "No specific rule for clean scrap",
    "review_required": False,
    "reuse_recommended_processor_id": None,
}

FAKE_ROUTING_NO_PICK = {
    "slider_w": 0.5, "candidates": [], "unscored_candidates": [],
    "picked_processor_id": None, "explanation": "no data",
    "rule_name": "Unclassified", "review_required": True,
    "reuse_recommended_processor_id": None,
}


def test_receipt_default_case_is_zero_credit():
    receipt = report.counterfactual_receipt(make_item(), FAKE_ROUTING_WITH_PICK)
    assert receipt.default_case.co2e_kg == 0.0
    assert receipt.default_case.value_inr == 0.0


def test_receipt_diff_equals_chosen_minus_default():
    receipt = report.counterfactual_receipt(make_item(), FAKE_ROUTING_WITH_PICK)
    assert receipt.diff_rupees == receipt.chosen_case.value_inr - receipt.default_case.value_inr
    assert receipt.diff_co2e_kg == receipt.chosen_case.co2e_kg - receipt.default_case.co2e_kg
    assert receipt.diff_rupees == 3270.0
    assert receipt.diff_co2e_kg == 140.0


def test_receipt_with_no_pick_has_no_diff():
    receipt = report.counterfactual_receipt(make_item(), FAKE_ROUTING_NO_PICK)
    assert receipt.diff_rupees is None
    assert receipt.diff_co2e_kg is None
    assert receipt.chosen_case.co2e_kg is None


def test_receipt_carries_emission_factor_source_and_proxy_label():
    receipt = report.counterfactual_receipt(make_item(material="steel_scrap"), FAKE_ROUTING_WITH_PICK)
    assert receipt.emission_factor_available is True
    assert receipt.emission_factor_label == "US proxy, not India-specific"
    assert "EPA WARM" in receipt.emission_factor_source


def test_receipt_flags_missing_emission_factor_honestly():
    receipt = report.counterfactual_receipt(make_item(material="copper_scrap"), FAKE_ROUTING_WITH_PICK)
    assert receipt.emission_factor_available is False
    assert receipt.emission_factor_label is None


def test_receipt_price_range_is_low_high_not_a_single_number():
    receipt = report.counterfactual_receipt(make_item(material="steel_scrap"), FAKE_ROUTING_WITH_PICK)
    assert receipt.price_range is not None
    assert receipt.price_range.low_inr_per_kg <= receipt.price_range.high_inr_per_kg
    assert receipt.price_range.source
    assert receipt.price_range.as_of


def test_receipt_price_range_is_none_when_material_unpriced():
    receipt = report.counterfactual_receipt(make_item(material="battery_lithium"), FAKE_ROUTING_NO_PICK)
    assert receipt.price_range is None


def test_dashboard_sums_kg_by_tier_and_co2e():
    routed = [(make_item(quantity_kg=100.0), FAKE_ROUTING_WITH_PICK)]
    summary = report.dashboard_summary(routed)
    assert summary["kg_by_tier"]["recycle"] == 100.0
    assert summary["co2e_avoided_kg"] == 140.0
    assert summary["compliance_status"] == "no items pending review"
    assert "Routing aid only" in summary["disclaimer"]


def test_dashboard_flags_pending_review():
    routed = [(make_item(material="other", quantity_kg=5.0), FAKE_ROUTING_NO_PICK)]
    summary = report.dashboard_summary(routed)
    assert summary["compliance_status"] == "some items pending human review"
