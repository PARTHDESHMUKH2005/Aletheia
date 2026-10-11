"""Guardrails enforced in code, never only in the prompt (BUILD.md section 5),
following RULES.md sections 2-4 (E-Waste, Hazardous Waste, Battery rules) and
section 9 (things LoopBack must never claim).

Wording constraints (RULES.md section 4 / section 9):
- Never write "compliant", "approved" or "certified" anywhere user-facing.
- Never state a processor is authorized unless authorization_checked_on is present.
- The storage-device wipe requirement is LoopBack policy, not a legal requirement --
  phrase it that way in any user-facing text.
"""

FORBIDDEN_WORDS = ("compliant", "approved", "certified")

ROUTING_DISCLAIMER = (
    "Routing aid only. Confirm rules and processor authorization with the "
    "official CPCB or State Board source."
)

STORAGE_DEVICE_POLICY_NOTE = (
    "LoopBack policy: a storage device is held until a data wipe is confirmed. "
    "This is not a legal requirement, it is a precaution we chose."
)

LITHIUM_FIRE_RISK_WARNING = (
    "Lithium battery: fire risk. Store away from heat, do not puncture or crush."
)

_ALWAYS_REVIEW_MATERIALS = {"battery_lead_acid", "battery_lithium", "used_oil", "mixed_metal"}

_CONTAMINATION_KEYWORDS = ("oil", "chemical", "battery", "batteries", "solvent", "acid", "mercury")

_CLEAN_METAL_MATERIALS = {"aluminium_scrap", "steel_scrap", "copper_scrap"}

# Out of LoopBack scope entirely (RULES.md section 7): refused and flagged, not just reviewed.
_OUT_OF_SCOPE_KEYWORDS = {
    "bio_medical": ("biomedical", "bio-medical", "medical waste", "clinical waste", "syringe", "needle", "sharps"),
    "radioactive": ("radioactive", "radiation"),
    "explosive": ("explosive", "detonator", "ammunition", "munition"),
    "biological": ("biohazard", "pathogen", "biological waste"),
}


def _item_text(item) -> str:
    return f"{item.composition_note} {item.reasoning}".lower()


def out_of_scope_flag(item) -> str | None:
    """Returns the out-of-scope category if the item's description matches one, else None.

    These categories are refused outright, not routed and not merely reviewed.
    """
    text = _item_text(item)
    for label, keywords in _OUT_OF_SCOPE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return label
    return None


def needs_review(item, rule: dict) -> bool:
    """Combines the rule row's review_required with LoopBack-specific always-review triggers."""
    if rule["review_required"] or item.hazardous:
        return True
    if item.material in _ALWAYS_REVIEW_MATERIALS:
        return True
    if item.material in _CLEAN_METAL_MATERIALS:
        text = _item_text(item)
        if any(keyword in text for keyword in _CONTAMINATION_KEYWORDS):
            return True
    return False


def fire_risk_warning(item) -> str | None:
    if item.material == "battery_lithium":
        return LITHIUM_FIRE_RISK_WARNING
    return None


def _needs_registered_handler(processor: dict, material: str) -> bool:
    """E-waste handed to a refurbisher, dismantler or recycler needs a registered handler
    (RULES.md section 2). Plain reuse/donation does not, so reuse-tier processors are exempt.
    """
    return material.startswith("e_waste") and processor.get("tier") != "reuse"


def processor_authorized_for(processor: dict, material: str, hazardous: bool) -> bool:
    """A processor may take a hazardous/regulated item only if it accepts the material
    AND carries both authorization_ref and authorization_checked_on. Missing the check
    date means the authorization is treated as unverified, not as absent -- either way,
    the item is refused for that processor and goes to review.
    """
    if material not in processor.get("accepted_materials", []):
        return False
    intrinsically_hazardous = material in ("battery_lead_acid", "battery_lithium", "used_oil")
    if not hazardous and not intrinsically_hazardous and not _needs_registered_handler(processor, material):
        return True
    return bool(processor.get("authorization_ref")) and bool(processor.get("authorization_checked_on"))


DEMO_AUTHORIZATION_LABEL = "demo only, authorization not checked"


def authorization_label(processor: dict) -> str:
    """User-facing authorization text. Without a reference it is always the demo
    label; with one it only reports what is on file, never a verdict.
    """
    ref = processor.get("authorization_ref")
    if not ref:
        return DEMO_AUTHORIZATION_LABEL
    checked_on = processor.get("authorization_checked_on")
    if not checked_on:
        return f"authorization reference on file ({ref}) but never checked"
    return f"authorization reference on file ({ref}), last checked {checked_on}; confirm with the official CPCB or State Board source"


def can_advance_storage_device(item, ledger_events: list[str]) -> bool:
    """LoopBack policy (STORAGE_DEVICE_POLICY_NOTE), not a legal requirement: a storage
    device cannot move past 'requested' until a data_wipe_confirmed ledger event exists.
    """
    if not item.is_storage_device:
        return True
    return "data_wipe_confirmed" in ledger_events


def sanitize_wording(text: str) -> str:
    """Raises if user-facing text contains a forbidden compliance word."""
    lowered = text.lower()
    for word in FORBIDDEN_WORDS:
        if word in lowered:
            raise ValueError(f"forbidden word '{word}' in user-facing text: {text!r}")
    return text
