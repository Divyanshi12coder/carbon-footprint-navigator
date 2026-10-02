"""Monthly behaviour profiles.

A behaviour profile is a list of (emission factor, monthly quantity) pairs describing what a
user typically does in a month. It is derived from tracked activities when there are enough, and
from onboarding answers otherwise (cold start). Scenarios and recommendations are computed on top
of it with the same emission factors the calculation engine uses.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.carbon.factors import FactorNotFoundError, get_active_factor
from app.models import EmissionRecord, UserProfile

DAYS_PER_MONTH = 30.4375
TRACKED_WINDOW_DAYS = 90
# Flights and big purchases are lumpy: annualise them over a longer window so one trip isn't multiplied x4.
INFREQUENT_WINDOW_DAYS = 365
INFREQUENT_PREFIXES = ("flights.", "consumption.", "business.")
MIN_TRACKED_DAYS = 14
MIN_TRACKED_RECORDS = 5

# Assumptions used only for the onboarding (profile-based) estimate.
SHORT_HAUL_RETURN_KM = 2 * 1100.0
LONG_HAUL_RETURN_KM = 2 * 7500.0
HEATING_OIL_KWH_PER_L = 10.35
LPG_KWH_PER_L = 7.08
SHOPPING_LEVEL_SPEND_USD = {"low": 40.0, "medium": 120.0, "high": 300.0}
RECYCLING_SHARE = {"none": 0.0, "some": 0.3, "most": 0.6}
COMPOST_SHARE = 0.15


@dataclass
class BehaviorItem:
    factor_key: str
    category: str
    monthly_quantity: float  # in factor units
    unit: str
    factor_value: float
    region: str = "GLOBAL"
    activity_count: int = 0  # tracked activities in the window (0 for profile estimates)
    window_days: int = 0  # days of tracking the monthly rate was derived from (0 for profile estimates)

    @property
    def monthly_kg(self) -> float:
        return self.monthly_quantity * self.factor_value


@dataclass
class BehaviorProfile:
    basis: str  # "tracked_activities" | "onboarding_profile" | "none"
    items: list[BehaviorItem] = field(default_factory=list)
    window_days: int = 0
    assumptions: list[str] = field(default_factory=list)
    region: str | None = None

    @property
    def monthly_total_kg(self) -> float:
        return sum(i.monthly_kg for i in self.items)

    def by_category(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for item in self.items:
            totals[item.category] = totals.get(item.category, 0.0) + item.monthly_kg
        return totals

    def items_with_prefix(self, prefix: str) -> list[BehaviorItem]:
        return [i for i in self.items if i.factor_key.startswith(prefix)]


def _aggregate(db: Session, user_id: uuid.UUID, start: date, end: date) -> dict[tuple[str, str, str], tuple[float, float, int]]:
    """(factor_key, category, unit) -> (normalized quantity, kg, count) for personal records in [start, end]."""
    rows = db.execute(
        select(
            EmissionRecord.factor_key,
            EmissionRecord.category,
            EmissionRecord.factor_unit,
            func.sum(EmissionRecord.normalized_quantity),
            func.sum(EmissionRecord.co2e_kg),
            func.count(EmissionRecord.id),
        )
        .where(
            EmissionRecord.user_id == user_id,
            EmissionRecord.organization_id.is_(None),
            EmissionRecord.occurred_on >= start,
            EmissionRecord.occurred_on <= end,
        )
        .group_by(EmissionRecord.factor_key, EmissionRecord.category, EmissionRecord.factor_unit)
    ).all()
    return {(k, c, u): (float(q or 0), float(kg or 0), int(n)) for k, c, u, q, kg, n in rows}


def tracked_profile(db: Session, user_id: uuid.UUID, today: date | None = None) -> BehaviorProfile:
    today = today or date.today()
    first = db.scalar(
        select(func.min(EmissionRecord.occurred_on)).where(EmissionRecord.user_id == user_id, EmissionRecord.organization_id.is_(None))
    )
    if first is None:
        return BehaviorProfile(basis="none")
    history_days = (today - first).days + 1
    window = max(1, min(TRACKED_WINDOW_DAYS, history_days))
    long_window = max(1, min(INFREQUENT_WINDOW_DAYS, history_days))
    routine = _aggregate(db, user_id, today - timedelta(days=window - 1), today)
    infrequent = _aggregate(db, user_id, today - timedelta(days=long_window - 1), today)
    items = []
    total_count = 0
    for key in sorted(set(routine) | set(infrequent)):
        is_infrequent = key[0].startswith(INFREQUENT_PREFIXES)
        source, w = (infrequent, long_window) if is_infrequent else (routine, window)
        if key not in source:
            continue
        qty, kg, count = source[key]
        total_count += count
        # Effective factor = kg / qty (identical to the stored factor unless it was versioned mid-window).
        factor_value = kg / qty if qty > 0 else 0.0
        items.append(BehaviorItem(key[0], key[1], qty * DAYS_PER_MONTH / w, key[2], factor_value, activity_count=count, window_days=w))
    profile = BehaviorProfile(basis="tracked_activities", items=items, window_days=window)
    profile.assumptions.append(f"Routine activities: monthly rate from the last {window} day(s) of tracking.")
    if long_window > window or any(i.factor_key.startswith(INFREQUENT_PREFIXES) for i in items):
        profile.assumptions.append(
            f"Infrequent activities (flights, product purchases, hotel stays, shopping) averaged over {long_window} day(s)."
        )
    if window < MIN_TRACKED_DAYS or total_count < MIN_TRACKED_RECORDS:
        profile.assumptions.append("Limited tracking history — estimates will stabilise as you log more activities.")
    return profile


def has_enough_tracking(profile: BehaviorProfile) -> bool:
    return (
        profile.basis == "tracked_activities"
        and profile.window_days >= MIN_TRACKED_DAYS
        and sum(i.activity_count for i in profile.items) >= MIN_TRACKED_RECORDS
    )


def onboarding_profile(db: Session, profile: UserProfile | None) -> BehaviorProfile:
    result = BehaviorProfile(basis="onboarding_profile", window_days=0)
    if profile is None:
        result.basis = "none"
        return result
    region = profile.country
    result.region = region
    household = max(1, profile.household_size or 1)

    def add(key: str, monthly_qty: float, region_lookup: str | None = None) -> None:
        if monthly_qty <= 0:
            return
        try:
            factor, _ = get_active_factor(db, key, region_lookup)
        except FactorNotFoundError:
            return
        result.items.append(BehaviorItem(key, factor.category, monthly_qty, factor.unit, factor.co2e_per_unit, factor.region))

    weeks_per_month = DAYS_PER_MONTH / 7
    if profile.weekly_car_km:
        vehicle = profile.vehicle_type if profile.vehicle_type not in (None, "none") else "petrol"
        if profile.vehicle_type in (None, "none"):
            result.assumptions.append("Car type not given — petrol car assumed.")
        add(f"transport.car.{vehicle}", profile.weekly_car_km * weeks_per_month)
    if profile.weekly_public_transport_km:
        monthly = profile.weekly_public_transport_km * weeks_per_month
        add("transport.bus", monthly / 2)
        add("transport.rail", monthly / 2)
        result.assumptions.append("Public transport split 50/50 between bus and rail.")
    if profile.short_haul_flights_per_year:
        add("flights.short_haul.economy", profile.short_haul_flights_per_year * SHORT_HAUL_RETURN_KM / 12)
        result.assumptions.append("Each short-haul flight = economy return trip of 2 x 1,100 km.")
    if profile.long_haul_flights_per_year:
        add("flights.long_haul.economy", profile.long_haul_flights_per_year * LONG_HAUL_RETURN_KM / 12)
        result.assumptions.append("Each long-haul flight = economy return trip of 2 x 7,500 km.")

    if profile.monthly_electricity_kwh:
        per_person = profile.monthly_electricity_kwh / household
        share = (profile.renewable_share_pct or 0) / 100
        add("energy.electricity.grid", per_person * (1 - share), region)
        add("energy.electricity.renewable", per_person * share)
        if household > 1:
            result.assumptions.append(f"Household energy and waste divided by household size ({household}).")
    if profile.monthly_heating_kwh and profile.heating_fuel not in (None, "none"):
        per_person = profile.monthly_heating_kwh / household
        fuel = profile.heating_fuel
        if fuel == "natural_gas":
            add("energy.natural_gas", per_person)
        elif fuel == "heating_oil":
            add("energy.heating_oil", per_person / HEATING_OIL_KWH_PER_L)
        elif fuel == "lpg":
            add("energy.lpg", per_person / LPG_KWH_PER_L)
        elif fuel == "electric":
            add("energy.electricity.grid", per_person, region)

    if profile.diet_type:
        add(f"food.diet_day.{profile.diet_type}", DAYS_PER_MONTH)

    if profile.monthly_clothing_spend_usd:
        add("consumption.spend.clothing", profile.monthly_clothing_spend_usd)
    if profile.monthly_electronics_spend_usd:
        add("consumption.spend.electronics", profile.monthly_electronics_spend_usd)
    if (
        not profile.monthly_clothing_spend_usd
        and not profile.monthly_electronics_spend_usd
        and profile.shopping_level in SHOPPING_LEVEL_SPEND_USD
    ):
        spend = SHOPPING_LEVEL_SPEND_USD[profile.shopping_level]
        add("consumption.spend.clothing", spend / 2)
        add("consumption.spend.household_goods", spend / 2)
        result.assumptions.append(
            f"'{profile.shopping_level}' shopping level assumed to be ${spend:.0f}/month, split clothing/household goods."
        )

    if profile.weekly_waste_kg:
        monthly = profile.weekly_waste_kg * weeks_per_month / household
        recycled = RECYCLING_SHARE.get(profile.recycling_level or "none", 0.0)
        composted = COMPOST_SHARE if profile.composts else 0.0
        add("waste.recycling", monthly * recycled)
        add("waste.composting", monthly * composted)
        add("waste.landfill", monthly * (1 - recycled - composted))
        result.assumptions.append("Recycling level mapped to share recycled: none 0%, some 30%, most 60%; composting 15%.")

    if not result.items:
        result.basis = "none"
    return result


def best_profile(db: Session, user_id: uuid.UUID, user_profile: UserProfile | None, today: date | None = None) -> BehaviorProfile:
    """Tracked data when there is enough of it, otherwise the onboarding estimate."""
    tracked = tracked_profile(db, user_id, today)
    if has_enough_tracking(tracked):
        return tracked
    fallback = onboarding_profile(db, user_profile)
    if fallback.basis != "none":
        return fallback
    return tracked
