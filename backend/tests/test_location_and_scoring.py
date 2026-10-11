"""Pincode lookup, hard-fail distance, fixed-scale scoring, distance cap, authorization labels."""
import json
import socket
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import pipeline
from app.main import app
from app.models import Characterization, Item
from app.storage.local import LocalStorage
from app.tools import geo, matching
from app.tools.geo import InvalidCoordinatesError, LocationError, UnknownPincodeError

DATA = Path(matching.__file__).resolve().parent.parent / "data"
PATIALA = geo.resolve_pincode("147001")

REQUIRED_PINCODES = {
    "147001": "Patiala", "147004": "Patiala", "141001": "Ludhiana", "160017": "Chandigarh",
    "133001": "Ambala", "143001": "Amritsar", "144001": "Jalandhar", "110001": "Delhi",
    "122001": "Gurugram", "147301": "Mandi Gobindgarh",
}


def make_item(material="steel_scrap", **kw) -> Item:
    base = dict(material=material, composition_note="clean scrap", quantity_kg=100.0, quantity_basis="stated",
                purity="high", hazardous=False, is_storage_device=False, confidence=0.9, reasoning="clean")
    base.update(kw)
    return Item(**base)


def proc(pid, name, price, recovery, lat=30.0, lng=76.0, material="steel_scrap"):
    return {"id": pid, "name": name, "location": {"lat": lat, "lng": lng, "address": "x"},
            "accepted_materials": [material], "tier": "recycle", "price_per_kg_inr": price,
            "recovery_rate": recovery, "authorization_ref": None, "authorization_checked_on": None, "seeded": True}


@pytest.fixture
def factor_2(monkeypatch):
    monkeypatch.setattr(matching, "get_avoided_factor",
                        lambda m: {"avoided_kg_co2e_per_kg": 2.0, "source": "t", "label": "t", "verified": True})


def use(monkeypatch, procs):
    monkeypatch.setattr(matching, "_PROCESSORS", procs)


# ---------- 1. pincode path ----------

def test_required_pincodes_present_with_plausible_coordinates():
    for code, city in REQUIRED_PINCODES.items():
        point = geo.resolve_pincode(code)
        assert point["address"].startswith(city)
        assert 8 < point["lat"] < 37 and 68 < point["lng"] < 98  # inside India's bounding box


def test_unknown_pincode_error_names_the_problem_and_lists_available():
    with pytest.raises(UnknownPincodeError) as exc:
        geo.resolve_pincode("999999")
    msg = str(exc.value)
    assert "Pincode not in demo data" in msg and "999999" in msg
    for code in REQUIRED_PINCODES:
        assert code in msg


@pytest.mark.parametrize("bad", [None, "", "  "])
def test_missing_pincode_is_an_error_too(bad):
    with pytest.raises(UnknownPincodeError, match="Pincode not in demo data"):
        geo.resolve_pincode(bad)


def test_every_processor_has_a_pincode_in_the_table_near_its_coordinates():
    table = json.loads((DATA / "pincodes_demo.json").read_text())["pincodes"]
    for p in json.loads((DATA / "processors.json").read_text()):
        assert p.get("pincode") in table, p["id"]
        assert matching.haversine_km(p["location"], table[p["pincode"]]) < 30, p["id"]


def test_lookup_never_touches_the_network(monkeypatch):
    def no_network(*a, **k):
        raise AssertionError("network call attempted")
    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket.socket, "connect", no_network)
    geo.resolve_pincode("147001")
    with pytest.raises(UnknownPincodeError):
        geo.resolve_pincode("999999")


def test_pipeline_uses_the_pincode_not_the_org(monkeypatch):
    seen = {}
    from app import agent as agent_mod
    real = agent_mod.find_processors
    def spy(item, loc, **k):
        seen["loc"] = loc
        return real(item, loc, **k)
    monkeypatch.setattr(agent_mod, "find_processors", spy)
    monkeypatch.setattr(pipeline, "characterize_waste", lambda *a, **k: Characterization(items=[make_item()], overall_confidence=0.9))
    with tempfile.TemporaryDirectory() as tmp:
        st = LocalStorage(db_path=Path(tmp) / "t.db")
        st.save_upload("p.jpg", b"x")
        # org_campus_workshop is in Patiala, but the request pincode says Amritsar
        st.create_stream("s", {"org_id": "org_campus_workshop", "photo_keys": ["p.jpg"], "pincode": "143001",
                               "slider_w": 0.5, "status": "SUBMITTED"})
        pipeline.run_pipeline("s", storage=st)
    assert seen["loc"]["pincode"] == "143001"
    assert seen["loc"]["lat"] == pytest.approx(31.6340)


def test_pipeline_unknown_pincode_fails_with_clear_message_and_no_model_call(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("characterize should not run for a bad pincode")
    monkeypatch.setattr(pipeline, "characterize_waste", boom)
    with tempfile.TemporaryDirectory() as tmp:
        st = LocalStorage(db_path=Path(tmp) / "t.db")
        st.save_upload("p.jpg", b"x")
        st.create_stream("s", {"org_id": "org_campus_workshop", "photo_keys": ["p.jpg"], "pincode": "000000",
                               "slider_w": 0.5, "status": "SUBMITTED"})
        result = pipeline.run_pipeline("s", storage=st)
    assert result["status"] == "FAILED"
    assert "Pincode not in demo data" in result["error"] and "147001" in result["error"]


def test_api_rejects_unknown_and_missing_pincode_with_422():
    client = TestClient(app)
    for body in ({"pincode": "000000"}, {}):
        resp = client.post("/streams", json={"org_id": "org_campus_workshop", "photo_keys": ["x.jpg"], **body})
        assert resp.status_code == 422
        assert "Pincode not in demo data" in resp.json()["detail"]


def test_demo_readme_states_coordinates_are_approximate_area_centres():
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text().lower()
    assert "approximate area centres" in readme


# ---------- 2. no silent zero distance ----------

@pytest.mark.parametrize("bad", [
    {}, {"lat": None, "lng": None}, {"lat": 30.0}, {"lat": "30", "lng": 76.0},
    {"lat": float("nan"), "lng": 76.0}, {"lat": 91.0, "lng": 76.0}, {"lat": 30.0, "lng": 181.0}, {"lat": True, "lng": 76.0},
])
def test_haversine_raises_on_missing_or_invalid_coordinates(bad):
    with pytest.raises(InvalidCoordinatesError):
        matching.haversine_km(bad, PATIALA)
    with pytest.raises(InvalidCoordinatesError):
        matching.haversine_km(PATIALA, bad)


def test_find_processors_propagates_the_error_instead_of_zero_distance():
    with pytest.raises(LocationError, match="Missing or invalid lat"):
        matching.find_processors(make_item(), {"lat": None, "lng": None})


def test_pipeline_turns_bad_coordinates_into_a_failed_stream_with_message(monkeypatch):
    monkeypatch.setattr(pipeline, "resolve_pincode", lambda p: {"lat": None, "lng": None})
    monkeypatch.setattr(pipeline, "characterize_waste", lambda *a, **k: Characterization(items=[make_item()], overall_confidence=0.9))
    with tempfile.TemporaryDirectory() as tmp:
        st = LocalStorage(db_path=Path(tmp) / "t.db")
        st.save_upload("p.jpg", b"x")
        st.create_stream("s", {"org_id": "o", "photo_keys": ["p.jpg"], "pincode": "147001", "slider_w": 0.5, "status": "SUBMITTED"})
        result = pipeline.run_pipeline("s", storage=st)
    assert result["status"] == "FAILED"
    assert "Cannot compute a distance" in result["error"]


def test_haversine_patiala_to_ludhiana_is_about_80km():
    assert matching.haversine_km(PATIALA, geo.resolve_pincode("141001")) == pytest.approx(80.4, abs=1.0)


# ---------- 3. scoring ----------

def test_scores_use_fixed_reference_not_min_max(monkeypatch, factor_2):
    # Two near-identical options: min-max would spread them to 0 and 1; a fixed scale keeps them near 1.
    use(monkeypatch, [proc("a", "A", 100.0, 0.90), proc("b", "B", 97.0, 0.90)])
    r = matching.find_processors(make_item(), {"lat": 30.0, "lng": 76.0}, w=0.0)
    scores = {c["processor_id"]: c for c in r["candidates"]}
    assert scores["a"]["money_score"] == pytest.approx(1.0)
    assert scores["b"]["money_score"] == pytest.approx(0.97)
    assert r["picked_processor_id"] == "a"


def test_reference_best_includes_processors_beyond_the_cap(monkeypatch, factor_2):
    use(monkeypatch, [proc("near", "Near", 50.0, 0.90), proc("far", "Far", 100.0, 0.90, lat=40.0)])
    r = matching.find_processors(make_item(), {"lat": 30.0, "lng": 76.0}, w=0.0)
    assert r["picked_processor_id"] == "near"
    near = r["candidates"][0]
    assert near["money_score"] < 0.55  # scaled against the far (better-paying) option, not itself


def test_raw_scores_are_returned(monkeypatch, factor_2):
    use(monkeypatch, [proc("a", "A", 100.0, 0.95), proc("b", "B", 80.0, 0.85)])
    r = matching.find_processors(make_item(), {"lat": 30.0, "lng": 76.0}, w=0.5)
    for c in r["candidates"]:
        for key in ("money_score", "carbon_score", "money_score_used", "carbon_score_used", "score",
                    "net_rupees_per_kg", "net_co2e_per_kg"):
            assert isinstance(c[key], float)
    assert r["reference_scale"]["best_net_rupees_per_kg"] == pytest.approx(100.0)
    assert set(r["measures_treated_equal"]) == {"money", "carbon"}


def test_spread_under_two_percent_is_treated_as_equal(monkeypatch, factor_2):
    # money differs by 1% (equal), carbon differs a lot -> carbon alone decides even at w=0.
    use(monkeypatch, [proc("m", "More money", 100.0, 0.50), proc("c", "More carbon", 99.0, 0.95)])
    r = matching.find_processors(make_item(), {"lat": 30.0, "lng": 76.0}, w=0.0)
    assert r["measures_treated_equal"] == {"money": True, "carbon": False}
    assert r["picked_processor_id"] == "c"
    assert "treated as equal" in r["explanation"]
    raw = {c["processor_id"]: c for c in r["candidates"]}
    assert raw["c"]["money_score"] == pytest.approx(0.99)         # raw score still reported
    assert raw["c"]["money_score_used"] == raw["m"]["money_score_used"] == pytest.approx(1.0)


def test_spread_just_over_two_percent_is_not_equal(monkeypatch, factor_2):
    use(monkeypatch, [proc("m", "More money", 100.0, 0.50), proc("c", "More carbon", 97.0, 0.95)])
    r = matching.find_processors(make_item(), {"lat": 30.0, "lng": 76.0}, w=0.0)
    assert r["measures_treated_equal"]["money"] is False
    assert r["picked_processor_id"] == "m"


def test_ties_break_by_nearer_distance_then_name_and_say_so(monkeypatch, factor_2):
    org = {"lat": 30.0, "lng": 76.0}
    use(monkeypatch, [proc("far", "Alpha", 100.0, 0.9, lat=30.5), proc("near", "Zulu", 100.0, 0.9, lat=30.2)])
    r = matching.find_processors(make_item(), org, w=0.5)
    # prices equal, but transport makes near slightly better; both within 2% -> equal -> tie -> nearer wins
    assert r["picked_processor_id"] == "near"
    assert "tie broken by nearer distance" in r["explanation"]
    assert "name" in r["tie_break_rule"]

    use(monkeypatch, [proc("p2", "Bravo", 100.0, 0.9), proc("p1", "Alpha", 100.0, 0.9)])
    r = matching.find_processors(make_item(), org, w=0.5)
    assert [c["name"] for c in r["candidates"]] == ["Alpha", "Bravo"]
    assert r["picked_processor_id"] == "p1"
    assert "tie broken by" in r["explanation"]


# ---------- 4. distance cap and real-data slider ----------

def test_candidates_beyond_cap_are_not_ranked(monkeypatch, factor_2):
    use(monkeypatch, [proc("near", "Near", 50.0, 0.9), proc("far", "Far", 100.0, 0.9, lat=40.0)])
    r = matching.find_processors(make_item(), {"lat": 30.0, "lng": 76.0}, w=0.0)
    assert [c["processor_id"] for c in r["candidates"]] == ["near"]
    far = r["unscored_candidates"][0]
    assert far["processor_id"] == "far" and "beyond max distance of 500 km" in far["reason_unscored"]


def test_cap_is_configurable_by_argument_and_env(monkeypatch, factor_2):
    use(monkeypatch, [proc("near", "Near", 50.0, 0.9), proc("far", "Far", 100.0, 0.9, lat=40.0)])
    org = {"lat": 30.0, "lng": 76.0}
    assert matching.find_processors(make_item(), org, max_distance_km=2000)["max_distance_km"] == 2000
    assert len(matching.find_processors(make_item(), org, max_distance_km=2000)["candidates"]) == 2
    monkeypatch.setenv("MAX_DISTANCE_KM", "100")
    r = matching.find_processors(make_item(), org)
    assert r["max_distance_km"] == 100 and len(r["candidates"]) == 1
    monkeypatch.setenv("MAX_DISTANCE_KM", "abc")
    with pytest.raises(ValueError, match="MAX_DISTANCE_KM"):
        matching.find_processors(make_item(), org)


def test_default_cap_is_500(monkeypatch):
    monkeypatch.delenv("MAX_DISTANCE_KM", raising=False)
    assert matching.default_max_distance_km() == 500.0


def test_no_buyer_within_cap_gives_no_pick_and_says_why(monkeypatch, factor_2):
    use(monkeypatch, [proc("far", "Far", 100.0, 0.9, lat=40.0)])
    r = matching.find_processors(make_item(), {"lat": 30.0, "lng": 76.0})
    assert r["picked_processor_id"] is None and "within 500 km" in r["explanation"]


@pytest.mark.parametrize("material", ["aluminium_scrap", "steel_scrap"])
def test_real_data_slider_flips_between_two_buyers_within_250km_of_patiala(material):
    item = make_item(material=material)
    picks = {w: matching.find_processors(item, PATIALA, w=w) for w in (0, 0.25, 0.5, 0.75, 1)}
    assert picks[0]["picked_processor_id"] != picks[1]["picked_processor_id"]
    for w in (0, 1):
        assert len(picks[w]["candidates"]) >= 2
        assert all(c["distance_km"] <= 250 for c in picks[w]["candidates"])
        assert not any(c["distance_km"] > 500 for c in picks[w]["candidates"])


def test_seeded_recovery_rates_are_in_realistic_band_and_labelled():
    for p in json.loads((DATA / "processors.json").read_text()):
        if p["tier"] == "disposal":
            continue
        if p["tier"] in ("recycle", "recovery"):
            assert 0.85 <= p["recovery_rate"] <= 0.95, p["id"]
        assert p["recovery_rate_basis"] == "illustrative_assumption", p["id"]


# ---------- 5. authorization labels ----------

def test_every_unreferenced_processor_is_labelled_demo_only():
    client = TestClient(app)
    rows = client.get("/processors").json()
    assert rows
    for row in rows:
        if not row.get("authorization_ref"):
            assert row["authorization_label"] == "demo only, authorization not checked"


def test_candidates_carry_the_label_and_no_output_says_authorized():
    r = matching.find_processors(make_item("aluminium_scrap"), PATIALA)
    assert all(c["authorization_label"] == "demo only, authorization not checked" for c in r["candidates"])
    text = json.dumps(r).lower() + json.dumps(TestClient(app).get("/processors").json()).lower()
    assert "authorized" not in text


def test_label_with_a_reference_reports_what_is_on_file_not_a_verdict():
    from app.tools.guardrails import authorization_label
    label = authorization_label({"authorization_ref": "XYZ-1", "authorization_checked_on": "2026-01-01"})
    assert "XYZ-1" in label and "authorized" not in label.lower()
    assert "never checked" in authorization_label({"authorization_ref": "XYZ-1", "authorization_checked_on": None})


# ---------- paper / cardboard produce a real receipt ----------

@pytest.mark.parametrize("material", ["paper", "cardboard"])
def test_paper_and_cardboard_route_and_slider_flips_within_250km(material):
    from app.tools.report import counterfactual_receipt
    item = make_item(material=material, quantity_kg=20.0)
    lo, hi = (matching.find_processors(item, PATIALA, w=w) for w in (0.0, 1.0))
    assert lo["picked_processor_id"] and hi["picked_processor_id"]
    assert lo["picked_processor_id"] != hi["picked_processor_id"]
    assert all(c["distance_km"] <= 250 for c in lo["candidates"])
    receipt = counterfactual_receipt(item, lo)
    assert receipt.chosen_case.value_inr and receipt.chosen_case.value_inr > 0
    assert receipt.chosen_case.co2e_kg and receipt.chosen_case.co2e_kg > 0
    assert receipt.diff_rupees is not None and receipt.diff_co2e_kg is not None
    assert "unverified" in receipt.emission_factor_label  # estimate stays labelled, not passed off as WARM
