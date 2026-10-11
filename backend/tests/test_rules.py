import json
from pathlib import Path

from app.tools.rules import _RULES, lookup_rules

RULES_PATH = Path(__file__).resolve().parent.parent / "app" / "data" / "rules.json"


def test_unknown_material_returns_other_row_and_needs_review():
    result = lookup_rules("some_material_not_in_the_table")
    other = lookup_rules("other")
    assert result == other
    assert result["review_required"] is True


def test_lookup_rules_never_returns_a_fabricated_section_ref():
    known_refs = {row["section_ref"] for row in _RULES if row["section_ref"] is not None}
    for row in _RULES:
        result = lookup_rules(row["material"])
        returned_ref = result.get("section_ref")
        assert returned_ref is None or returned_ref in known_refs


def test_every_rule_with_m_in_basis_is_unverified():
    for row in _RULES:
        result = lookup_rules(row["material"])
        if "M" in row["basis"]:
            assert result["verified"] is False, row["material"]


def test_paper_and_cardboard_use_current_solid_waste_rules():
    for material in ("paper", "cardboard"):
        result = lookup_rules(material)
        assert "Solid Waste Management Rules, 2026" in result["rule_name"]
        assert "5(1)(b)" in result["section_ref"]
        assert result["regulated"] is True


def test_aluminium_and_copper_require_review_for_conditional_epr_scope():
    for material in ("aluminium_scrap", "copper_scrap"):
        result = lookup_rules(material)
        assert "HOTWM Rules, 2016 as amended 2025" in result["section_ref"]
        assert result["review_required"] is True
        assert result["verified"] is False


def test_battery_routes_are_reviewed_without_claiming_every_battery_is_hazardous_waste():
    for material in ("battery_lead_acid", "battery_lithium"):
        result = lookup_rules(material)
        assert "as amended through 2025" in result["rule_name"]
        assert "r. 5" in result["section_ref"]
        assert result["review_required"] is True
        assert result["verified"] is False
        assert any("not a legal classification" in text for text in result["key_requirements"])


def test_rules_json_only_has_materials_from_the_build_md_enum():
    allowed = {
        "aluminium_scrap", "steel_scrap", "copper_scrap", "mixed_metal",
        "paper", "cardboard", "e_waste_computer", "e_waste_storage_drive",
        "e_waste_other", "battery_lead_acid", "battery_lithium",
        "used_oil", "other",
    }
    materials = {row["material"] for row in json.loads(RULES_PATH.read_text())}
    assert materials <= allowed
    assert materials == allowed
