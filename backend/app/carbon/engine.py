"""Deterministic carbon calculation engine.

    co2e_kg = normalized_quantity x factor_value

where ``normalized_quantity`` is the activity quantity converted to the factor's unit and
allocated to the user (car occupancy share, passengers, return trips). That invariant holds for
every stored EmissionRecord and is what makes each number traceable.
No language model is involved in any calculation here.
"""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.carbon import flights
from app.carbon.catalog import ActivityTypeSpec, ActivityValidationError, category_for, get_spec, normalise_details
from app.carbon.factors import FactorNotFoundError, get_active_factor
from app.carbon.units import UnitConversionError, convert
from app.models import EmissionFactor

_QUALITY_ORDER = {"high": 2, "medium": 1, "low": 0}
_QUALITY_NAMES = {v: k for k, v in _QUALITY_ORDER.items()}


class CalculationError(ValueError):
    """Raised for invalid inputs; surfaced to clients as HTTP 422."""


@dataclass
class CalculationResult:
    activity_type: str
    category: str
    details: dict[str, Any]
    quantity: float
    unit: str
    factor: EmissionFactor | None
    factor_key: str
    factor_value: float
    factor_unit: str
    factor_source: str
    factor_region: str
    normalized_quantity: float
    co2e_kg: float
    calculation_method: str
    data_quality: str
    assumptions: list[str] = field(default_factory=list)


def _downgrade(quality: str, steps: int = 1) -> str:
    return _QUALITY_NAMES[max(0, _QUALITY_ORDER[quality] - steps)]


def _fmt(x: float) -> str:
    return f"{x:,.4f}".rstrip("0").rstrip(".")


def calculate(
    db: Session,
    activity_type: str,
    quantity: float | None,
    unit: str | None,
    details: dict[str, Any] | None,
    region: str | None = None,
) -> CalculationResult:
    try:
        spec = get_spec(activity_type)
        clean = normalise_details(spec, details or {})
    except ActivityValidationError as exc:
        raise CalculationError(str(exc)) from exc

    if spec.mode == "flight":
        return _calculate_flight(db, spec, quantity, unit, clean)
    if spec.mode == "custom":
        return _calculate_custom(spec, quantity, unit, clean)

    if quantity is None or quantity < 0:
        raise CalculationError("Quantity must be zero or a positive number.")
    unit = unit or spec.units[0]
    if unit not in spec.units:
        raise CalculationError(f"Unit '{unit}' is not valid for {spec.label}. Use one of: {', '.join(spec.units)}.")

    key = spec.resolve(clean)
    lookup_region = region if key.startswith("energy.electricity.grid") else None
    try:
        factor, used_fallback = get_active_factor(db, key, lookup_region)
        converted = convert(quantity, unit, factor.unit)
    except (FactorNotFoundError, UnitConversionError) as exc:
        raise CalculationError(str(exc)) from exc

    assumptions: list[str] = []
    quality = factor.quality
    normalized = converted.value
    method = f"{_fmt(quantity)} {unit}"
    if converted.multiplier != 1:
        method += f" x {_fmt(converted.multiplier)} = {_fmt(converted.value)} {factor.unit}"
    if unit == "m3":
        assumptions.append("Natural gas volume converted at 10.83 kWh/m3 (gross calorific value).")

    occupants = clean.get("occupants")
    if activity_type == "car" and occupants and occupants > 1:
        normalized = converted.value / occupants
        method += f" / {int(occupants)} occupants"
        assumptions.append(f"Vehicle emissions split equally between {int(occupants)} occupants.")
    if used_fallback:
        quality = _downgrade(quality)
        assumptions.append(f"No grid factor for region '{region}'; global average used.")

    co2e = normalized * factor.co2e_per_unit
    method += f" x {_fmt(factor.co2e_per_unit)} kg CO2e/{factor.unit} = {co2e:,.3f} kg CO2e"
    return CalculationResult(
        activity_type=activity_type,
        category=category_for(spec, clean),
        details=clean,
        quantity=quantity,
        unit=unit,
        factor=factor,
        factor_key=factor.key,
        factor_value=factor.co2e_per_unit,
        factor_unit=factor.unit,
        factor_source=factor.source,
        factor_region=factor.region,
        normalized_quantity=normalized,
        co2e_kg=co2e,
        calculation_method=method,
        data_quality=quality,
        assumptions=assumptions,
    )


def _calculate_flight(
    db: Session, spec: ActivityTypeSpec, quantity: float | None, unit: str | None, clean: dict[str, Any]
) -> CalculationResult:
    assumptions: list[str] = []
    origin, destination = clean.get("origin"), clean.get("destination")
    route = ""
    if origin or destination:
        if not (origin and destination):
            raise CalculationError("Provide both origin and destination airports, or a distance instead.")
        a, b = flights.get_airport(origin), flights.get_airport(destination)
        missing = [c for c, ap in ((origin, a), (destination, b)) if ap is None]
        if missing:
            raise CalculationError(f"Unknown airport code(s): {', '.join(missing)}. Enter the flight distance instead.")
        if origin == destination:
            raise CalculationError("Origin and destination must be different airports.")
        gc = flights.great_circle_km(a, b)  # type: ignore[arg-type]
        distance_km = gc * flights.ROUTING_UPLIFT
        route = f"great-circle {origin}->{destination} {gc:,.0f} km x {flights.ROUTING_UPLIFT} routing uplift"
        assumptions.append(f"Distance {origin}->{destination} computed from airport coordinates with 8% routing uplift.")
        quantity, unit = round(distance_km, 1), "km"
    else:
        if quantity is None or quantity <= 0:
            raise CalculationError("Enter the flight distance, or origin and destination airports.")
        unit = unit or "km"
        if unit not in spec.units:
            raise CalculationError(f"Unit '{unit}' is not valid for flights. Use km or mi.")
        distance_km = convert(quantity, unit, "km").value
        route = f"{_fmt(distance_km)} km entered"

    haul = flights.haul_for_distance(distance_km)
    key, note = flights.factor_key_for(haul, clean["cabin_class"])
    if note:
        assumptions.append(note)
    try:
        factor, _ = get_active_factor(db, key)
    except FactorNotFoundError as exc:
        raise CalculationError(str(exc)) from exc

    passengers = int(clean.get("passengers") or 1)
    legs = 2 if clean.get("round_trip") else 1
    normalized = distance_km * passengers * legs
    co2e = normalized * factor.co2e_per_unit
    method = (
        f"{route} = {distance_km:,.1f} km x {passengers} passenger(s) x {legs} leg(s) = {normalized:,.1f} passenger-km "
        f"x {_fmt(factor.co2e_per_unit)} kg CO2e/passenger-km ({haul.replace('_', '-')}) = {co2e:,.3f} kg CO2e"
    )
    clean = {**clean, "distance_km": round(distance_km, 1), "haul": haul}
    return CalculationResult(
        activity_type=spec.key,
        category=spec.category,
        details=clean,
        quantity=float(quantity),
        unit=unit,
        factor=factor,
        factor_key=factor.key,
        factor_value=factor.co2e_per_unit,
        factor_unit=factor.unit,
        factor_source=factor.source,
        factor_region=factor.region,
        normalized_quantity=normalized,
        co2e_kg=co2e,
        calculation_method=method,
        data_quality=factor.quality,
        assumptions=assumptions,
    )


def _calculate_custom(spec: ActivityTypeSpec, quantity: float | None, unit: str | None, clean: dict[str, Any]) -> CalculationResult:
    if quantity is None or quantity < 0:
        raise CalculationError("Quantity must be zero or a positive number.")
    unit = (unit or "unit").strip()[:24] or "unit"
    factor_value = float(clean["factor_kg_per_unit"])
    source = clean.get("factor_source") or "User-supplied factor"
    co2e = quantity * factor_value
    return CalculationResult(
        activity_type=spec.key,
        category=category_for(spec, clean),
        details=clean,
        quantity=quantity,
        unit=unit,
        factor=None,
        factor_key="custom.user_supplied",
        factor_value=factor_value,
        factor_unit=unit,
        factor_source=source[:300],
        factor_region="N/A",
        normalized_quantity=quantity,
        co2e_kg=co2e,
        calculation_method=f"{_fmt(quantity)} {unit} x {_fmt(factor_value)} kg CO2e/{unit} = {co2e:,.3f} kg CO2e",
        data_quality="low",
        assumptions=["Emission factor supplied by the user; not verified against a reference dataset."],
    )
