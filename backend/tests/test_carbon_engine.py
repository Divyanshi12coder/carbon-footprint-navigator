import pytest

from app.carbon import flights
from app.carbon.engine import CalculationError, calculate
from app.carbon.factors import FactorNotFoundError, get_active_factor


def test_petrol_car_uses_factor_from_table(db):
    factor, _ = get_active_factor(db, "transport.car.petrol")
    r = calculate(db, "car", 100, "km", {"fuel_type": "petrol"})
    assert r.co2e_kg == pytest.approx(100 * factor.co2e_per_unit)
    assert r.factor is not None and r.factor.id == factor.id
    assert r.category == "transport"
    assert "kg CO2e" in r.calculation_method


def test_invariant_co2e_equals_normalized_quantity_times_factor(db):
    cases = [
        ("car", 42, "mi", {"fuel_type": "diesel", "occupants": 3}),
        ("electricity", 250, "kWh", {"source": "grid"}),
        ("natural_gas", 30, "m3", {}),
        ("meal", 3, "serving", {"meal_type": "beef"}),
        ("waste", 10, "lb", {"method": "landfill"}),
        ("flight", None, None, {"origin": "LHR", "destination": "JFK", "cabin_class": "business", "round_trip": True}),
    ]
    for activity_type, qty, unit, details in cases:
        r = calculate(db, activity_type, qty, unit, details, region="GB")
        assert r.co2e_kg == pytest.approx(r.normalized_quantity * r.factor_value), activity_type


def test_unit_conversion_miles(db):
    km = calculate(db, "car", 160.9344, "km", {"fuel_type": "petrol"})
    mi = calculate(db, "car", 100, "mi", {"fuel_type": "petrol"})
    assert mi.co2e_kg == pytest.approx(km.co2e_kg)


def test_occupancy_shares_emissions(db):
    solo = calculate(db, "car", 100, "km", {"fuel_type": "petrol", "occupants": 1})
    shared = calculate(db, "car", 100, "km", {"fuel_type": "petrol", "occupants": 4})
    assert shared.co2e_kg == pytest.approx(solo.co2e_kg / 4)
    assert any("occupants" in a for a in shared.assumptions)


def test_electricity_regional_factor_and_fallback(db):
    gb, _ = get_active_factor(db, "energy.electricity.grid", "GB")
    global_f, _ = get_active_factor(db, "energy.electricity.grid")
    r_gb = calculate(db, "electricity", 100, "kWh", {"source": "grid"}, region="GB")
    assert r_gb.co2e_kg == pytest.approx(100 * gb.co2e_per_unit)
    assert r_gb.factor_region == "GB"

    r_unknown = calculate(db, "electricity", 100, "kWh", {"source": "grid"}, region="KE")
    assert r_unknown.factor_region == "GLOBAL"
    assert r_unknown.co2e_kg == pytest.approx(100 * global_f.co2e_per_unit)
    assert r_unknown.data_quality in ("medium", "low")
    assert any("global average" in a for a in r_unknown.assumptions)


def test_flight_distance_and_haul(db):
    gc = flights.great_circle_km(flights.get_airport("LHR"), flights.get_airport("JFK"))
    assert 5500 < gc < 5600  # published great-circle distance ~5,540 km
    r = calculate(db, "flight", None, None, {"origin": "lhr", "destination": "jfk", "cabin_class": "economy", "passengers": 2})
    assert r.factor_key == "flights.long_haul.economy"
    assert r.normalized_quantity == pytest.approx(gc * flights.ROUTING_UPLIFT * 2)
    rt = calculate(
        db, "flight", None, None, {"origin": "LHR", "destination": "JFK", "cabin_class": "economy", "passengers": 2, "round_trip": True}
    )
    assert rt.co2e_kg == pytest.approx(2 * r.co2e_kg)


def test_short_haul_and_distance_only_flights(db):
    r = calculate(db, "flight", None, None, {"origin": "LHR", "destination": "BCN", "cabin_class": "economy"})
    assert r.factor_key == "flights.short_haul.economy"
    d = calculate(db, "flight", 300, "km", {"cabin_class": "economy"})
    assert d.factor_key == "flights.domestic.average"


def test_flight_validation_errors(db):
    with pytest.raises(CalculationError, match="Unknown airport"):
        calculate(db, "flight", None, None, {"origin": "LHR", "destination": "ZZZ", "cabin_class": "economy"})
    with pytest.raises(CalculationError):
        calculate(db, "flight", None, None, {"cabin_class": "economy"})
    with pytest.raises(CalculationError, match="different"):
        calculate(db, "flight", None, None, {"origin": "LHR", "destination": "LHR", "cabin_class": "economy"})


def test_invalid_inputs_raise(db):
    with pytest.raises(CalculationError, match="Unknown activity type"):
        calculate(db, "teleport", 1, "km", {})
    with pytest.raises(CalculationError, match="Unit"):
        calculate(db, "car", 10, "kWh", {"fuel_type": "petrol"})
    with pytest.raises(CalculationError, match="not a valid"):
        calculate(db, "car", 10, "km", {"fuel_type": "steam"})
    with pytest.raises(CalculationError):
        calculate(db, "car", -5, "km", {"fuel_type": "petrol"})


def test_zero_emission_active_travel(db):
    r = calculate(db, "active_travel", 12, "km", {"mode": "bicycle"})
    assert r.co2e_kg == 0


def test_custom_factor_is_low_quality(db):
    r = calculate(db, "custom", 4, "widgets", {"factor_kg_per_unit": 2.5, "custom_category": "consumption"})
    assert r.co2e_kg == pytest.approx(10)
    assert r.category == "consumption"
    assert r.data_quality == "low"
    assert r.factor is None


def test_missing_factor_raises(db):
    with pytest.raises(FactorNotFoundError):
        get_active_factor(db, "does.not.exist")


def test_every_catalog_resolution_has_a_factor(db):
    """Every select option in the activity catalogue must map to an active seeded factor."""
    from app.carbon.catalog import CATALOG

    for spec in CATALOG.values():
        if spec.mode != "standard":
            continue
        selects = [f for f in spec.fields if f.type == "select"]
        options = [{}] if not selects else [{selects[0].name: c.value} for c in selects[0].choices]
        for details in options:
            r = calculate(db, spec.key, 1, spec.units[0], details)
            assert r.factor is not None, (spec.key, details)
