from app.models import Item
from app.tools import guardrails
from app.tools.rules import lookup_rules


def make_item(**overrides) -> Item:
    defaults = dict(
        material="steel_scrap",
        composition_note="clean steel can",
        quantity_kg=1.0,
        quantity_basis="estimated",
        purity="high",
        hazardous=False,
        is_storage_device=False,
        confidence=0.9,
        reasoning="looks like a clean steel can",
    )
    defaults.update(overrides)
    return Item(**defaults)


def test_hazardous_item_to_processor_without_authorization_ref_is_refused():
    processor = {"accepted_materials": ["used_oil"], "authorization_ref": None, "authorization_checked_on": None}
    assert guardrails.processor_authorized_for(processor, "used_oil", hazardous=True) is False


def test_processor_with_ref_but_no_checked_on_date_is_treated_as_unverified():
    processor = {
        "accepted_materials": ["used_oil"],
        "authorization_ref": "CPCB/HW/12345",
        "authorization_checked_on": None,
    }
    assert guardrails.processor_authorized_for(processor, "used_oil", hazardous=True) is False


def test_processor_with_ref_and_checked_on_date_is_authorized():
    processor = {
        "accepted_materials": ["used_oil"],
        "authorization_ref": "CPCB/HW/12345",
        "authorization_checked_on": "2026-09-01",
    }
    assert guardrails.processor_authorized_for(processor, "used_oil", hazardous=True) is True


def test_non_hazardous_item_does_not_need_authorization_date():
    processor = {"accepted_materials": ["steel_scrap"], "authorization_ref": None, "authorization_checked_on": None}
    assert guardrails.processor_authorized_for(processor, "steel_scrap", hazardous=False) is True


def test_storage_device_cannot_move_without_wipe_event():
    drive = make_item(material="e_waste_storage_drive", is_storage_device=True)
    assert guardrails.can_advance_storage_device(drive, ledger_events=["requested"]) is False
    assert guardrails.can_advance_storage_device(drive, ledger_events=["requested", "data_wipe_confirmed"]) is True


def test_non_storage_device_has_no_wipe_restriction():
    scrap = make_item(is_storage_device=False)
    assert guardrails.can_advance_storage_device(scrap, ledger_events=[]) is True


def test_battery_and_used_oil_always_need_review():
    for material in ("battery_lead_acid", "battery_lithium", "used_oil"):
        item = make_item(material=material, hazardous=True)
        rule = lookup_rules(material)
        assert guardrails.needs_review(item, rule) is True


def test_lithium_battery_gets_fire_risk_warning():
    item = make_item(material="battery_lithium", hazardous=True)
    assert guardrails.fire_risk_warning(item) == guardrails.LITHIUM_FIRE_RISK_WARNING


def test_lead_acid_battery_has_no_fire_risk_warning():
    item = make_item(material="battery_lead_acid", hazardous=True)
    assert guardrails.fire_risk_warning(item) is None


def test_mixed_metal_always_needs_review():
    item = make_item(material="mixed_metal")
    rule = lookup_rules("mixed_metal")
    assert guardrails.needs_review(item, rule) is True


def test_clean_metal_with_contamination_mention_needs_review():
    item = make_item(material="steel_scrap", composition_note="steel drum, smells of used oil")
    rule = lookup_rules("steel_scrap")
    assert guardrails.needs_review(item, rule) is True


def test_clean_metal_without_contamination_mention_does_not_need_review():
    item = make_item(material="steel_scrap", composition_note="clean steel can, no residue")
    rule = lookup_rules("steel_scrap")
    assert guardrails.needs_review(item, rule) is False


def test_bio_medical_waste_is_flagged_out_of_scope():
    item = make_item(material="other", composition_note="box of used syringes and needles")
    assert guardrails.out_of_scope_flag(item) == "bio_medical"


def test_ordinary_item_is_not_out_of_scope():
    item = make_item()
    assert guardrails.out_of_scope_flag(item) is None


def test_sanitize_wording_rejects_forbidden_words():
    import pytest

    for word in ("compliant", "approved", "certified"):
        with pytest.raises(ValueError):
            guardrails.sanitize_wording(f"This processor is {word}.")


def test_sanitize_wording_passes_clean_text():
    assert guardrails.sanitize_wording(guardrails.ROUTING_DISCLAIMER) == guardrails.ROUTING_DISCLAIMER
