"""Unit conversion into the base unit an emission factor is expressed in."""

from dataclasses import dataclass


class UnitConversionError(ValueError):
    pass


# factor base unit -> {accepted input unit: multiplier into base unit}
_CONVERSIONS: dict[str, dict[str, float]] = {
    "km": {"km": 1.0, "mi": 1.609344},
    "passenger_km": {"km": 1.0, "mi": 1.609344, "passenger_km": 1.0},
    "kWh": {
        "kWh": 1.0,
        "MWh": 1000.0,
        "MJ": 1 / 3.6,
        "therm": 29.3071,
        # Natural gas only: DESNZ 2024 gross CV of ~39 MJ/m3 => ~10.83 kWh/m3.
        "m3": 10.83,
    },
    "L": {"L": 1.0, "gal": 3.785411},
    "kg": {"kg": 1.0, "lb": 0.45359237, "t": 1000.0},
    "serving": {"serving": 1.0},
    "day": {"day": 1.0},
    "USD": {"USD": 1.0},
    "item": {"item": 1.0},
    "hour": {"hour": 1.0, "min": 1 / 60},
    "room_night": {"room_night": 1.0, "night": 1.0},
}


@dataclass(frozen=True)
class Converted:
    value: float
    base_unit: str
    multiplier: float


def convert(quantity: float, unit: str, base_unit: str) -> Converted:
    table = _CONVERSIONS.get(base_unit)
    if table is None:
        raise UnitConversionError(f"No conversions defined for base unit '{base_unit}'.")
    if unit not in table:
        allowed = ", ".join(sorted(table))
        raise UnitConversionError(f"Unit '{unit}' cannot be converted to '{base_unit}'. Allowed: {allowed}.")
    multiplier = table[unit]
    return Converted(value=quantity * multiplier, base_unit=base_unit, multiplier=multiplier)


def is_convertible(unit: str, base_unit: str) -> bool:
    return unit in _CONVERSIONS.get(base_unit, {})
