import pytest

from app.carbon.behavior import BehaviorItem, BehaviorProfile, onboarding_profile
from app.carbon.factors import get_active_factor
from app.carbon.scenarios import FactorCache, ScenarioLevers, simulate
from app.ml import recommendations
from app.models import UserProfile
from tests.conftest import add_activity


def _f(db, key, region=None):
    return get_active_factor(db, key, region)[0].co2e_per_unit


def _profile(db, items):
    out = []
    for key, qty in items:
        factor, _ = get_active_factor(db, key, "GB")
        out.append(BehaviorItem(key, factor.category, qty, factor.unit, factor.co2e_per_unit, window_days=90, activity_count=12))
    return BehaviorProfile(basis="tracked_activities", items=out, window_days=90, region="GB")


def test_flight_reduction_halves_flight_emissions(db):
    p = _profile(db, [("flights.long_haul.economy", 1000), ("transport.car.petrol", 400)])
    res = simulate(db, p, ScenarioLevers(flight_reduction_pct=50))
    assert res.reduction_monthly_kg == pytest.approx(500 * _f(db, "flights.long_haul.economy"), rel=1e-3)
    assert res.scenario_by_category["transport"] == res.current_by_category["transport"]


def test_meat_substitution_uses_vegetarian_factor(db):
    p = _profile(db, [("food.meal.beef", 10)])
    res = simulate(db, p, ScenarioLevers(meat_reduction_pct=50))
    expected = 5 * (_f(db, "food.meal.beef") - _f(db, "food.meal.vegetarian"))
    assert res.reduction_monthly_kg == pytest.approx(expected, rel=1e-3)


def test_renewable_and_ev_and_recycling(db):
    p = _profile(db, [("energy.electricity.grid", 300), ("transport.car.petrol", 500), ("waste.landfill", 40)])
    res = simulate(db, p, ScenarioLevers(renewable_share_pct=100))
    assert res.reduction_monthly_kg == pytest.approx(
        300 * (_f(db, "energy.electricity.grid", "GB") - _f(db, "energy.electricity.renewable")), rel=1e-3
    )
    ev = simulate(db, p, ScenarioLevers(ev_adoption_pct=100))
    assert ev.reduction_monthly_kg == pytest.approx(500 * (_f(db, "transport.car.petrol") - _f(db, "transport.car.electric")), rel=1e-3)
    rec = simulate(db, p, ScenarioLevers(recycling_improvement_pct=50))
    assert rec.reduction_monthly_kg == pytest.approx(20 * (_f(db, "waste.landfill") - _f(db, "waste.recycling")), rel=1e-3)


def test_combined_levers_and_effects(db):
    p = _profile(db, [("flights.short_haul.economy", 500), ("transport.car.petrol", 600), ("food.diet_day.mixed", 30)])
    noop = simulate(db, p, ScenarioLevers())
    assert noop.reduction_monthly_kg == 0
    res = simulate(db, p, ScenarioLevers(car_reduction_pct=20, flight_reduction_pct=100, meat_reduction_pct=100))
    assert 0 < res.reduction_pct < 100
    assert {e["lever"] for e in res.lever_effects} == {"car_reduction_pct", "flight_reduction_pct", "meat_reduction_pct"}
    assert res.scenario_monthly_kg == pytest.approx(res.current_monthly_kg - res.reduction_monthly_kg, abs=1e-2)


def test_recommendations_are_computed_from_factors(db):
    p = _profile(db, [("transport.car.petrol", 800), ("energy.electricity.grid", 250), ("food.meal.beef", 8), ("waste.landfill", 30)])
    recs = {r.rec_key: r for r in recommendations.generate(p, FactorCache(db, "GB"))}
    assert {"car_to_public_transport", "renewable_tariff", "swap_red_meat", "recycle_more"} <= set(recs)
    renewable = recs["renewable_tariff"]
    expected = 250 * (_f(db, "energy.electricity.grid", "GB") - _f(db, "energy.electricity.renewable"))
    assert renewable.estimated_monthly_reduction_kg == pytest.approx(expected, abs=0.01)
    beef = recs["swap_red_meat"]
    assert beef.estimated_monthly_reduction_kg == pytest.approx(4 * (_f(db, "food.meal.beef") - _f(db, "food.meal.vegetarian")), abs=0.01)
    for r in recs.values():
        assert r.calculation_basis and r.current_behavior and r.suggested_action
        assert r.difficulty in ("easy", "medium", "hard")
    ordered = recommendations.generate(p, FactorCache(db, "GB"))
    assert [r.priority_score for r in ordered] == sorted((r.priority_score for r in ordered), reverse=True)


def test_no_recommendations_without_behaviour(db):
    empty = BehaviorProfile(basis="none")
    assert recommendations.generate(empty, FactorCache(db, None)) == []


def test_onboarding_profile_estimate(db):
    prof = UserProfile(
        country="GB",
        household_size=2,
        vehicle_type="petrol",
        weekly_car_km=100,
        monthly_electricity_kwh=400,
        renewable_share_pct=50,
        diet_type="vegetarian",
        weekly_waste_kg=10,
        recycling_level="most",
    )
    est = onboarding_profile(db, prof)
    assert est.basis == "onboarding_profile"
    keys = {i.factor_key for i in est.items}
    assert {"transport.car.petrol", "energy.electricity.grid", "energy.electricity.renewable", "food.diet_day.vegetarian"} <= keys
    grid = next(i for i in est.items if i.factor_key == "energy.electricity.grid")
    assert grid.monthly_quantity == pytest.approx(400 / 2 * 0.5)
    assert est.assumptions


def test_scenario_api_uses_tracked_data(client, user):
    for d in range(20):
        add_activity(client, user["headers"], "car", 30, "km", days_ago=d, fuel_type="petrol")
    base = client.get("/api/scenarios/baseline", headers=user["headers"]).json()
    assert base["basis"] == "tracked_activities"
    resp = client.post("/api/scenarios/simulate", headers=user["headers"], json={"car_reduction_pct": 50})
    body = resp.json()
    assert resp.status_code == 200
    assert body["reduction_pct"] == pytest.approx(50, abs=0.01)
    assert "car_reduction_pct" in body["available_levers"]


def test_scenario_api_without_data_returns_409(client, user):
    assert client.post("/api/scenarios/simulate", headers=user["headers"], json={"car_reduction_pct": 10}).status_code == 409
