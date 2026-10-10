import pytest

from app.models import Item
from app.tools import matching


def make_item(**overrides) -> Item:
    defaults = dict(
        material="steel_scrap",
        composition_note="clean steel can",
        quantity_kg=100.0,
        quantity_basis="estimated",
        purity="high",
        hazardous=False,
        is_storage_device=False,
        confidence=0.9,
        reasoning="clean steel",
    )
    defaults.update(overrides)
    return Item(**defaults)


SYNTHETIC_PROCESSORS = [
    {
        "id": "proc_expensive_low_carbon",
        "name": "Expensive Low Carbon",
        "location": {"lat": 30.0, "lng": 76.0, "address": "near"},
        "accepted_materials": ["steel_scrap"],
        "tier": "recycle",
        "price_per_kg_inr": 100.0,
        "recovery_rate": 0.5,
        "authorization_ref": None,
        "authorization_checked_on": None,
        "seeded": True,
    },
    {
        "id": "proc_cheap_high_carbon",
        "name": "Cheap High Carbon",
        "location": {"lat": 30.0, "lng": 76.0, "address": "near"},
        "accepted_materials": ["steel_scrap"],
        "tier": "recycle",
        "price_per_kg_inr": 50.0,
        "recovery_rate": 0.95,
        "authorization_ref": None,
        "authorization_checked_on": None,
        "seeded": True,
    },
]

def _synthetic_steel_factor(material):
    if material == "steel_scrap":
        return {"avoided_kg_co2e_per_kg": 2.0, "source": "test", "label": "test", "verified": True}
    return None


def _no_factor(material):
    return None


ORG_LOCATION = {"lat": 30.0, "lng": 76.0}


def test_slider_at_zero_picks_the_money_leader(monkeypatch):
    monkeypatch.setattr(matching, "_PROCESSORS", SYNTHETIC_PROCESSORS)
    monkeypatch.setattr(matching, "get_avoided_factor", _synthetic_steel_factor)

    result = matching.find_processors(make_item(), ORG_LOCATION, w=0.0)
    assert result["picked_processor_id"] == "proc_expensive_low_carbon"


def test_slider_at_one_picks_the_carbon_leader(monkeypatch):
    monkeypatch.setattr(matching, "_PROCESSORS", SYNTHETIC_PROCESSORS)
    monkeypatch.setattr(matching, "get_avoided_factor", _synthetic_steel_factor)

    result = matching.find_processors(make_item(), ORG_LOCATION, w=1.0)
    assert result["picked_processor_id"] == "proc_cheap_high_carbon"


def test_changing_the_slider_can_change_the_pick(monkeypatch):
    monkeypatch.setattr(matching, "_PROCESSORS", SYNTHETIC_PROCESSORS)
    monkeypatch.setattr(matching, "get_avoided_factor", _synthetic_steel_factor)

    money_pick = matching.find_processors(make_item(), ORG_LOCATION, w=0.0)["picked_processor_id"]
    carbon_pick = matching.find_processors(make_item(), ORG_LOCATION, w=1.0)["picked_processor_id"]
    assert money_pick != carbon_pick


def test_zero_distance_means_zero_transport_cost_and_co2(monkeypatch):
    monkeypatch.setattr(matching, "_PROCESSORS", SYNTHETIC_PROCESSORS)
    monkeypatch.setattr(matching, "get_avoided_factor", _synthetic_steel_factor)

    result = matching.find_processors(make_item(quantity_kg=100.0), ORG_LOCATION, w=0.0)
    expensive = next(c for c in result["candidates"] + result["unscored_candidates"]
                      if c["processor_id"] == "proc_expensive_low_carbon")
    assert expensive["net_rupees"] == 100.0 * 100.0  # price * kg, no transport deduction at zero distance


def test_unauthorized_hazardous_candidate_is_unscored(monkeypatch):
    hazardous_processor = dict(SYNTHETIC_PROCESSORS[0])
    hazardous_processor["accepted_materials"] = ["used_oil"]
    monkeypatch.setattr(matching, "_PROCESSORS", [hazardous_processor])
    monkeypatch.setattr(matching, "get_avoided_factor", _no_factor)

    item = make_item(material="used_oil", hazardous=True, quantity_kg=10.0)
    result = matching.find_processors(item, ORG_LOCATION, w=0.5)
    assert result["candidates"] == []
    assert len(result["unscored_candidates"]) == 1
    assert "not authorization-checked" in result["unscored_candidates"][0]["reason_unscored"]
    assert result["review_required"] is True


def test_reusable_working_laptop_is_flagged_for_reuse(monkeypatch):
    reuse_processor = {
        "id": "proc_reuse",
        "name": "Reuse Center",
        "location": {"lat": 30.0, "lng": 76.0, "address": "near"},
        "accepted_materials": ["e_waste_computer"],
        "tier": "reuse",
        "price_per_kg_inr": 0.0,
        "recovery_rate": 0.98,
        "authorization_ref": None,
        "authorization_checked_on": None,
        "seeded": True,
    }
    monkeypatch.setattr(matching, "_PROCESSORS", [reuse_processor])
    monkeypatch.setattr(matching, "get_avoided_factor", _no_factor)

    item = make_item(
        material="e_waste_computer", quantity_kg=2.0, purity="high",
        composition_note="laptop, powers on, working condition", reasoning="screen works, boots fine",
    )
    result = matching.find_processors(item, ORG_LOCATION, w=0.0)
    assert result["reuse_recommended_processor_id"] == "proc_reuse"


def test_broken_device_is_not_flagged_for_reuse(monkeypatch):
    monkeypatch.setattr(matching, "_PROCESSORS", [])
    monkeypatch.setattr(matching, "get_avoided_factor", _no_factor)

    item = make_item(
        material="e_waste_computer", quantity_kg=2.0, purity="high",
        composition_note="laptop, broken, cracked screen", reasoning="does not power on",
    )
    result = matching.find_processors(item, ORG_LOCATION, w=0.0)
    assert result["reuse_recommended_processor_id"] is None


def test_haversine_known_distance():
    delhi = {"lat": 28.6139, "lng": 77.2090}
    mumbai = {"lat": 19.0760, "lng": 72.8777}
    km = matching.haversine_km(delhi, mumbai)
    assert 1100 < km < 1200  # real Delhi-Mumbai great-circle distance is ~1150 km


# No monkeypatching below -- real data/processors.json, data/prices.json and
# data/emission_factors.json. Gap-closing requirement: the slider must visibly
# flip the pick for real seeded data, not just synthetic fixtures.
ORG_LOCATION_PATIALA = {"lat": 30.3398, "lng": 76.3869}


@pytest.mark.parametrize("material", ["aluminium_scrap", "steel_scrap"])
def test_slider_flips_the_pick_on_real_seeded_data(material):
    item = make_item(material=material, quantity_kg=100.0)
    money_pick = matching.find_processors(item, ORG_LOCATION_PATIALA, w=0.0)["picked_processor_id"]
    carbon_pick = matching.find_processors(item, ORG_LOCATION_PATIALA, w=1.0)["picked_processor_id"]
    assert money_pick is not None
    assert carbon_pick is not None
    assert money_pick != carbon_pick
