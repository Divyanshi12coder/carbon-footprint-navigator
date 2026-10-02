"""'What if I…' scenario engine.

Applies behavioural levers to a monthly behaviour profile and recomputes emissions with the
same emission factors. Substitutions (e.g. beef meal -> vegetarian meal, landfill -> recycling,
petrol km -> EV km) use the substitute's own factor, so reductions are never simply assumed.
"""

from dataclasses import asdict, dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.carbon.behavior import BehaviorItem, BehaviorProfile
from app.carbon.factors import FactorNotFoundError, get_active_factor

MEAT_MEALS = ("food.meal.beef", "food.meal.lamb", "food.meal.pork", "food.meal.chicken")
MEAT_DIETS = ("food.diet_day.meat_heavy", "food.diet_day.mixed", "food.diet_day.low_meat")


@dataclass
class ScenarioLevers:
    car_reduction_pct: float = 0
    ev_adoption_pct: float = 0
    flight_reduction_pct: float = 0
    electricity_reduction_pct: float = 0
    renewable_share_pct: float = 0
    heating_reduction_pct: float = 0
    meat_reduction_pct: float = 0
    recycling_improvement_pct: float = 0

    def is_noop(self) -> bool:
        return all(v == 0 for v in asdict(self).values())


@dataclass
class ScenarioResult:
    basis: str
    current_monthly_kg: float
    scenario_monthly_kg: float
    reduction_monthly_kg: float
    reduction_pct: float
    current_by_category: dict[str, float]
    scenario_by_category: dict[str, float]
    lever_effects: list[dict[str, Any]] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)

    @property
    def current_annual_kg(self) -> float:
        return self.current_monthly_kg * 12

    @property
    def scenario_annual_kg(self) -> float:
        return self.scenario_monthly_kg * 12


class FactorCache:
    """Memoised factor lookups for substitutes."""

    def __init__(self, db: Session, region: str | None):
        self.db, self.region, self.cache = db, region, {}

    def value(self, key: str, regional: bool = False) -> float | None:
        cache_key = (key, regional)
        if cache_key not in self.cache:
            try:
                factor, _ = get_active_factor(self.db, key, self.region if regional else None)
                self.cache[cache_key] = factor.co2e_per_unit
            except FactorNotFoundError:
                self.cache[cache_key] = None
        return self.cache[cache_key]


def _clone(items: list[BehaviorItem]) -> list[BehaviorItem]:
    return [BehaviorItem(**{**i.__dict__}) for i in items]


def _add_quantity(items: list[BehaviorItem], key: str, category: str, unit: str, qty: float, factor: float) -> None:
    for item in items:
        if item.factor_key == key:
            # Blend so monthly_kg stays exact even if the factor differs slightly from the stored one.
            total_kg = item.monthly_kg + qty * factor
            item.monthly_quantity += qty
            item.factor_value = total_kg / item.monthly_quantity if item.monthly_quantity else factor
            return
    items.append(BehaviorItem(key, category, qty, unit, factor))


def apply_levers(items: list[BehaviorItem], levers: ScenarioLevers, factors: FactorCache) -> tuple[list[BehaviorItem], list[str]]:
    items = _clone(items)
    notes: list[str] = []

    # 1. Drive less.
    car_items = [i for i in items if i.factor_key.startswith("transport.car.")]
    if levers.car_reduction_pct:
        for item in car_items:
            item.monthly_quantity *= 1 - levers.car_reduction_pct / 100

    # 2. Switch remaining combustion-car km to an EV.
    if levers.ev_adoption_pct:
        ev = factors.value("transport.car.electric")
        if ev is None:
            notes.append("EV factor unavailable; EV lever ignored.")
        else:
            moved = 0.0
            for item in car_items:
                if item.factor_key == "transport.car.electric":
                    continue
                shift = item.monthly_quantity * levers.ev_adoption_pct / 100
                item.monthly_quantity -= shift
                moved += shift
            if moved:
                _add_quantity(items, "transport.car.electric", "transport", "km", moved, ev)

    # 3. Fly less.
    if levers.flight_reduction_pct:
        for item in items:
            if item.factor_key.startswith("flights."):
                item.monthly_quantity *= 1 - levers.flight_reduction_pct / 100

    # 4. Use less electricity, then 5. raise renewable share of what remains.
    elec_items = [i for i in items if i.factor_key.startswith("energy.electricity.")]
    if levers.electricity_reduction_pct:
        for item in elec_items:
            item.monthly_quantity *= 1 - levers.electricity_reduction_pct / 100
    if levers.renewable_share_pct:
        renewable_factor = factors.value("energy.electricity.renewable")
        total_kwh = sum(i.monthly_quantity for i in elec_items)
        renewable_kwh = sum(i.monthly_quantity for i in elec_items if i.factor_key == "energy.electricity.renewable")
        target = total_kwh * levers.renewable_share_pct / 100
        if renewable_factor is not None and target > renewable_kwh:
            shift = target - renewable_kwh
            for item in elec_items:
                if item.factor_key != "energy.electricity.renewable" and shift > 0:
                    moved = min(shift, item.monthly_quantity)
                    item.monthly_quantity -= moved
                    shift -= moved
            _add_quantity(items, "energy.electricity.renewable", "energy", "kWh", target - renewable_kwh, renewable_factor)
        elif renewable_factor is not None:
            notes.append("Renewable share is already at or above the selected level.")

    # 6. Heat less (thermostat / insulation).
    if levers.heating_reduction_pct:
        for item in items:
            if item.factor_key in ("energy.natural_gas", "energy.heating_oil", "energy.lpg"):
                item.monthly_quantity *= 1 - levers.heating_reduction_pct / 100

    # 7. Replace meat with vegetarian equivalents (substitution, not deletion).
    if levers.meat_reduction_pct:
        p = levers.meat_reduction_pct / 100
        veg_meal = factors.value("food.meal.vegetarian")
        veg_day = factors.value("food.diet_day.vegetarian")
        meals_moved = sum(i.monthly_quantity * p for i in items if i.factor_key in MEAT_MEALS)
        days_moved = sum(i.monthly_quantity * p for i in items if i.factor_key in MEAT_DIETS)
        for item in items:
            if item.factor_key in MEAT_MEALS or item.factor_key in MEAT_DIETS:
                item.monthly_quantity *= 1 - p
        if meals_moved and veg_meal is not None:
            _add_quantity(items, "food.meal.vegetarian", "food", "serving", meals_moved, veg_meal)
        if days_moved and veg_day is not None:
            _add_quantity(items, "food.diet_day.vegetarian", "food", "day", days_moved, veg_day)

    # 8. Divert landfill waste to recycling.
    if levers.recycling_improvement_pct:
        recycling = factors.value("waste.recycling")
        moved = 0.0
        for item in items:
            if item.factor_key == "waste.landfill":
                shift = item.monthly_quantity * levers.recycling_improvement_pct / 100
                item.monthly_quantity -= shift
                moved += shift
        if moved and recycling is not None:
            _add_quantity(items, "waste.recycling", "waste", "kg", moved, recycling)
            notes.append("Assumes diverted general waste is recyclable material.")

    return items, notes


def _by_category(items: list[BehaviorItem]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for item in items:
        totals[item.category] = totals.get(item.category, 0.0) + item.monthly_kg
    return {k: round(v, 3) for k, v in sorted(totals.items())}


LEVER_LABELS = {
    "car_reduction_pct": "Drive less",
    "ev_adoption_pct": "Switch car km to an EV",
    "flight_reduction_pct": "Fly less",
    "electricity_reduction_pct": "Use less electricity",
    "renewable_share_pct": "Renewable electricity",
    "heating_reduction_pct": "Reduce heating fuel",
    "meat_reduction_pct": "Replace meat with vegetarian",
    "recycling_improvement_pct": "Recycle more",
}


def simulate(db: Session, profile: BehaviorProfile, levers: ScenarioLevers, region: str | None = None) -> ScenarioResult:
    factors = FactorCache(db, region or profile.region)
    current = profile.monthly_total_kg
    new_items, notes = apply_levers(profile.items, levers, factors)
    scenario = sum(i.monthly_kg for i in new_items)

    effects = []
    for name, value in asdict(levers).items():
        if not value:
            continue
        isolated, _ = apply_levers(profile.items, ScenarioLevers(**{name: value}), factors)
        saving = current - sum(i.monthly_kg for i in isolated)
        effects.append({"lever": name, "label": LEVER_LABELS[name], "value": value, "monthly_reduction_kg": round(saving, 3)})
    effects.sort(key=lambda e: e["monthly_reduction_kg"], reverse=True)

    reduction = current - scenario
    return ScenarioResult(
        basis=profile.basis,
        current_monthly_kg=round(current, 3),
        scenario_monthly_kg=round(scenario, 3),
        reduction_monthly_kg=round(reduction, 3),
        reduction_pct=round(100 * reduction / current, 2) if current > 0 else 0.0,
        current_by_category=_by_category(profile.items),
        scenario_by_category=_by_category(new_items),
        lever_effects=effects,
        assumptions=[*profile.assumptions, *notes],
    )
