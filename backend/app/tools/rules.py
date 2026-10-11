"""lookup_rules tool: dictionary lookup over data/rules.json.

Source of truth for every field here is RULES.md, not this file. Do not add
materials, rule names, or section references here without updating RULES.md
and getting them from an official text first -- see RULES.md section 9.
"""
import json
from pathlib import Path

_RULES_PATH = Path(__file__).resolve().parent.parent / "data" / "rules.json"
_RULES: list[dict] = json.loads(_RULES_PATH.read_text())
_RULES_BY_MATERIAL: dict[str, dict] = {row["material"]: row for row in _RULES}
_KNOWN_SECTION_REFS: set = {row["section_ref"] for row in _RULES if row["section_ref"] is not None}

UNVERIFIED_LABEL = "Unverified, check the official text"


def _is_verified(basis: list[str]) -> bool:
    """True only if basis contains 'V' and does not contain 'M' (RULES.md section 0)."""
    return "V" in basis and "M" not in basis


def lookup_rules(material: str, hazardous: bool | None = None) -> dict:
    """Returns the compact rule row for a material: rule_name, handler_requirement,
    paperwork, review_required, basis, verified.

    Unknown materials fall back to the "other" row, which carries
    review_required=True, rather than raising.
    """
    row = _RULES_BY_MATERIAL.get(material, _RULES_BY_MATERIAL["other"])
    return {
        "rule_name": row["rule_name"],
        "section_ref": row.get("section_ref"),
        "hazardous": row.get("hazardous", False),
        "regulated": row.get("regulated", False),
        "handler_requirement": row["handler_requirement"],
        "paperwork": row["paperwork"],
        "key_requirements": row.get("key_requirements", []),
        "review_required": row["review_required"],
        "basis": row["basis"],
        "verified": _is_verified(row["basis"]),
    }


def unverified_label(rule_result: dict) -> str | None:
    """UI/report helper: the label every displayed rule must carry when verified is false."""
    return None if rule_result["verified"] else UNVERIFIED_LABEL
