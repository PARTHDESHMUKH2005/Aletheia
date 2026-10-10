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
