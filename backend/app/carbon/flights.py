"""Flight distance and haul classification."""

import csv
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

EARTH_RADIUS_KM = 6371.0088
# DESNZ recommends an 8% uplift on great-circle distance for indirect routing and stacking.
ROUTING_UPLIFT = 1.08
DOMESTIC_MAX_KM = 500.0
SHORT_HAUL_MAX_KM = 3700.0


@dataclass(frozen=True)
class Airport:
    iata: str
    name: str
    city: str
    country: str
    lat: float
    lon: float


@lru_cache
def airports() -> dict[str, Airport]:
    path = Path(__file__).parent / "data" / "airports.csv"
    with path.open(encoding="utf-8") as fh:
        return {
            row["iata"]: Airport(row["iata"], row["name"], row["city"], row["country"], float(row["lat"]), float(row["lon"]))
            for row in csv.DictReader(fh)
        }


def get_airport(code: str) -> Airport | None:
    return airports().get(code.strip().upper())


def great_circle_km(a: Airport, b: Airport) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a.lat, a.lon, b.lat, b.lon))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


def haul_for_distance(distance_km: float) -> str:
    """DESNZ factor bands applied by distance (one-way flight distance)."""
    if distance_km < DOMESTIC_MAX_KM:
        return "domestic"
    if distance_km < SHORT_HAUL_MAX_KM:
        return "short_haul"
    return "long_haul"


def factor_key_for(haul: str, cabin_class: str) -> tuple[str, str | None]:
    """Map (haul, cabin) to a factor key. Returns (key, assumption note if a substitution was made)."""
    if haul == "domestic":
        note = None if cabin_class == "economy" else "Domestic factor is an average across cabin classes."
        return "flights.domestic.average", note
    if haul == "short_haul":
        if cabin_class == "economy":
            return "flights.short_haul.economy", None
        if cabin_class == "premium_economy":
            return "flights.short_haul.economy", "No short-haul premium-economy factor; economy factor used."
        if cabin_class == "first":
            return "flights.short_haul.business", "No short-haul first-class factor; business factor used."
        return "flights.short_haul.business", None
    return f"flights.long_haul.{cabin_class}", None
