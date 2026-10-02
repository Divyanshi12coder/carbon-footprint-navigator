"""Personalised, explainable recommendation engine.

Every recommendation is computed from the user's monthly behaviour profile (tracked activities,
or onboarding answers on cold start) and the active emission factors:

    estimated_reduction = changed_quantity x (factor_current - factor_alternative)

Candidates are ranked by priority = monthly reduction x difficulty weight, so an easy change with a
solid saving can outrank a hard one with a slightly bigger saving. Behavioural coefficients that are
assumptions (e.g. "1 degree C lower thermostat ~ 8% less heating fuel") are spelled out in
``calculation_basis`` so nothing is hidden.
"""

from dataclasses import dataclass

from app.carbon.behavior import DAYS_PER_MONTH, LONG_HAUL_RETURN_KM, BehaviorProfile
from app.carbon.scenarios import MEAT_DIETS, FactorCache

DIFFICULTY_WEIGHT = {"easy": 1.0, "medium": 0.7, "hard": 0.45}
MIN_REDUCTION_KG = 0.5
WEEKS_PER_MONTH = DAYS_PER_MONTH / 7
COMBUSTION_CAR_KEYS = ("transport.car.petrol", "transport.car.diesel", "transport.car.hybrid", "transport.car.plugin_hybrid")
SHORT_FLIGHT_PREFIXES = ("flights.domestic", "flights.short_haul")
THERMOSTAT_SAVING = 0.08
ELECTRICITY_EFFICIENCY = 0.10
FOOD_WASTE_SHARE = 0.30
SECOND_HAND_SAVING = 0.90


@dataclass
class RecommendationCandidate:
    rec_key: str
    category: str
    title: str
    reason: str
    current_behavior: str
    suggested_action: str
    estimated_monthly_reduction_kg: float
    difficulty: str
    calculation_basis: str
    share_of_footprint_pct: float = 0.0
    priority_score: float = 0.0


def _sum(profile: BehaviorProfile, keys: tuple[str, ...] | None = None, prefix: tuple[str, ...] | None = None):
    items = [i for i in profile.items if (keys and i.factor_key in keys) or (prefix and i.factor_key.startswith(prefix))]
    qty = sum(i.monthly_quantity for i in items)
    kg = sum(i.monthly_kg for i in items)
    return items, qty, kg


def generate(profile: BehaviorProfile, factors: FactorCache) -> list[RecommendationCandidate]:
    recs: list[RecommendationCandidate] = []
    total = profile.monthly_total_kg
    tracked = profile.basis == "tracked_activities"

    # --- Transport -----------------------------------------------------------------------------
    car_items, car_km, car_kg = _sum(profile, keys=COMBUSTION_CAR_KEYS)
    if car_km > 0:
        f_car = car_kg / car_km
        bus, rail = factors.value("transport.bus"), factors.value("transport.rail")
        if bus is not None and rail is not None:
            f_transit = (bus + rail) / 2
            trips = sum(i.activity_count * DAYS_PER_MONTH / i.window_days for i in car_items if i.window_days)
            if trips >= 1:
                avg_trip = car_km / trips
                shifted_trips = min(2 * WEEKS_PER_MONTH, 0.5 * trips)
                shifted_km = shifted_trips * avg_trip
                current = f"~{car_km * 12 / 52:.0f} km/week by car across ~{trips * 12 / 52:.1f} trips (avg {avg_trip:.1f} km)"
                suggestion = f"Replace {shifted_trips * 12 / 52:.1f} car trips a week (~{shifted_km * 12 / 52:.0f} km) with bus or train"
            else:
                shifted_km = 0.25 * car_km
                current = f"~{car_km * 12 / 52:.0f} km/week by car"
                suggestion = f"Move a quarter of your car km (~{shifted_km * 12 / 52:.0f} km/week) to bus or train"
            saving = shifted_km * (f_car - f_transit)
            recs.append(
                RecommendationCandidate(
                    "car_to_public_transport",
                    "transport",
                    "Swap some car trips for public transport",
                    "Car travel is one of your main emission sources and public transport emits far less per km.",
                    current,
                    suggestion,
                    saving,
                    "medium",
                    f"{shifted_km:,.1f} km/month x ({f_car:.4f} car - {f_transit:.4f} bus/rail average) kg CO2e/km",
                )
            )
        recs.append(
            RecommendationCandidate(
                "car_trip_chaining",
                "transport",
                "Combine errands to drive 15% less",
                "Trip chaining and skipping short drives trims car mileage without changing your routine much.",
                f"~{car_km * 12 / 52:.0f} km/week by car",
                "Cut car mileage by 15% by combining trips and walking short hops",
                0.15 * car_kg,
                "easy",
                f"15% x {car_kg:,.2f} kg CO2e/month of car emissions (behavioural assumption: 15% reduction)",
            )
        )
        ev = factors.value("transport.car.electric")
        if ev is not None and car_km * 12 >= 3000:
            recs.append(
                RecommendationCandidate(
                    "switch_to_ev",
                    "transport",
                    "Consider an electric car for your next vehicle",
                    "You drive enough that the per-km difference between combustion and electric cars adds up.",
                    f"~{car_km * 12:,.0f} km/year in a combustion or hybrid car",
                    "Switch to a battery-electric car when you next replace your vehicle",
                    car_km * (f_car - ev),
                    "hard",
                    f"{car_km:,.1f} km/month x ({f_car:.4f} current - {ev:.4f} EV) kg CO2e/km (EV factor reflects grid mix)",
                )
            )

    # --- Flights -------------------------------------------------------------------------------
    _, short_pkm, short_kg = _sum(profile, prefix=SHORT_FLIGHT_PREFIXES)
    rail = factors.value("transport.rail")
    if short_pkm > 0 and rail is not None:
        f_flight = short_kg / short_pkm
        shifted = 0.5 * short_pkm
        recs.append(
            RecommendationCandidate(
                "short_flights_to_rail",
                "flights",
                "Take the train instead of short flights",
                "On routes under ~800 km rail is often comparable door-to-door and emits a fraction of flying.",
                f"~{short_pkm * 12:,.0f} passenger-km/year on domestic & short-haul flights",
                "Replace half of your short-haul flight distance with rail where routes exist",
                shifted * (f_flight - rail),
                "medium",
                f"{shifted:,.1f} passenger-km/month x ({f_flight:.4f} flight - {rail:.4f} rail) kg CO2e/passenger-km",
            )
        )
    long_items, long_pkm, long_kg = _sum(profile, prefix=("flights.long_haul",))
    if long_pkm > 0:
        f_long = long_kg / long_pkm
        if tracked:
            cut_pkm = 0.25 * long_pkm
            basis = f"25% x {long_pkm:,.1f} passenger-km/month x {f_long:.4f} kg CO2e/passenger-km"
            action = "Cut long-haul flying by a quarter (fewer, longer trips; virtual meetings)"
        else:
            cut_pkm = LONG_HAUL_RETURN_KM / 12
            basis = f"one 2 x 7,500 km return trip / 12 months = {cut_pkm:,.1f} passenger-km/month x {f_long:.4f}"
            action = "Take one fewer long-haul return trip per year"
        recs.append(
            RecommendationCandidate(
                "fewer_long_haul_flights",
                "flights",
                "Fly long-haul less often",
                "A single long-haul return flight can outweigh months of everyday emissions.",
                f"~{long_pkm * 12:,.0f} passenger-km/year on long-haul flights",
                action,
                cut_pkm * f_long,
                "hard",
                basis,
            )
        )
        premium = [i for i in long_items if i.factor_key.split(".")[-1] in ("premium_economy", "business", "first")]
        economy = factors.value("flights.long_haul.economy")
        if premium and economy is not None:
            p_pkm = sum(i.monthly_quantity for i in premium)
            p_kg = sum(i.monthly_kg for i in premium)
            recs.append(
                RecommendationCandidate(
                    "fly_economy",
                    "flights",
                    "Choose economy on long-haul flights",
                    "Premium cabins take more floor space per passenger, so each seat carries more of the flight's emissions.",
                    f"~{p_pkm * 12:,.0f} passenger-km/year in premium cabins",
                    "Book economy for long-haul trips",
                    p_kg - p_pkm * economy,
                    "medium",
                    f"{p_kg:,.2f} kg premium-cabin emissions - {p_pkm:,.1f} passenger-km x {economy:.4f} economy factor",
                )
            )

    # --- Energy --------------------------------------------------------------------------------
    grid_items, grid_kwh, grid_kg = _sum(profile, keys=("energy.electricity.grid",))
    renewable = factors.value("energy.electricity.renewable")
    if grid_kwh > 0 and renewable is not None:
        f_grid = grid_kg / grid_kwh
        recs.append(
            RecommendationCandidate(
                "renewable_tariff",
                "energy",
                "Switch to a renewable electricity tariff",
                "Your electricity comes from the grid; a certified renewable supply cuts its carbon intensity sharply.",
                f"~{grid_kwh:,.0f} kWh/month of grid electricity at {f_grid:.3f} kg CO2e/kWh",
                "Move to a certified renewable tariff or community/rooftop solar",
                grid_kwh * (f_grid - renewable),
                "easy",
                f"{grid_kwh:,.1f} kWh/month x ({f_grid:.4f} grid - {renewable:.4f} renewable lifecycle) kg CO2e/kWh",
            )
        )
    _, elec_kwh, elec_kg = _sum(profile, prefix=("energy.electricity",))
    if elec_kwh > 0:
        recs.append(
            RecommendationCandidate(
                "electricity_efficiency",
                "energy",
                "Trim electricity use by 10%",
                "Standby loads, efficient lighting and appliance settings typically save around a tenth of household use.",
                f"~{elec_kwh:,.0f} kWh/month",
                "LED lighting, smart plugs for standby loads, cold-wash laundry",
                ELECTRICITY_EFFICIENCY * elec_kg,
                "easy",
                f"10% x {elec_kg:,.2f} kg CO2e/month of electricity emissions (assumed achievable efficiency gain)",
            )
        )
    _, _, heat_kg = _sum(profile, keys=("energy.natural_gas", "energy.heating_oil", "energy.lpg"))
    if heat_kg > 0:
        recs.append(
            RecommendationCandidate(
                "thermostat_down",
                "energy",
                "Turn the thermostat down 1°C",
                "Each degree lower typically reduces heating fuel use by around 8%.",
                f"{heat_kg:,.1f} kg CO2e/month from heating fuel",
                "Lower your heating set-point by 1°C and heat rooms you use",
                THERMOSTAT_SAVING * heat_kg,
                "easy",
                f"8% x {heat_kg:,.2f} kg CO2e/month heating emissions (assumption: ~8% fuel saving per 1°C)",
            )
        )

    # --- Food ----------------------------------------------------------------------------------
    veg_meal = factors.value("food.meal.vegetarian")
    red_items, red_servings, red_kg = _sum(profile, keys=("food.meal.beef", "food.meal.lamb"))
    if red_servings > 0 and veg_meal is not None:
        swap = 0.5 * red_servings
        f_red = red_kg / red_servings
        recs.append(
            RecommendationCandidate(
                "swap_red_meat",
                "food",
                "Swap half your beef & lamb meals",
                "Ruminant meat has by far the highest footprint per serving of any common food.",
                f"~{red_servings * 12 / 52:.1f} beef/lamb meals per week",
                f"Replace ~{swap * 12 / 52:.1f} of them per week with vegetarian meals",
                swap * (f_red - veg_meal),
                "medium",
                f"{swap:,.1f} servings/month x ({f_red:.3f} beef/lamb - {veg_meal:.3f} vegetarian) kg CO2e/serving",
            )
        )
    veg_day = factors.value("food.diet_day.vegetarian")
    diet_items, diet_days, diet_kg = _sum(profile, keys=MEAT_DIETS)
    if diet_days > 0 and veg_day is not None:
        shifted = min(diet_days, 2 * WEEKS_PER_MONTH)
        f_diet = diet_kg / diet_days
        if f_diet > veg_day:
            recs.append(
                RecommendationCandidate(
                    "meat_free_days",
                    "food",
                    "Go meat-free two days a week",
                    "Shifting a couple of days to vegetarian eating lowers your food footprint without a full diet change.",
                    f"~{diet_days:,.0f} days/month on a meat-inclusive diet",
                    "Eat vegetarian on two days each week",
                    shifted * (f_diet - veg_day),
                    "medium",
                    f"{shifted:,.1f} days/month x ({f_diet:.2f} current diet - {veg_day:.2f} vegetarian) kg CO2e/day",
                )
            )

    # --- Waste ---------------------------------------------------------------------------------
    _, landfill_kg_waste, landfill_kg = _sum(profile, keys=("waste.landfill",))
    recycling = factors.value("waste.recycling")
    compost = factors.value("waste.composting")
    if landfill_kg_waste > 0 and recycling is not None:
        f_landfill = landfill_kg / landfill_kg_waste
        recs.append(
            RecommendationCandidate(
                "recycle_more",
                "waste",
                "Divert half of general waste to recycling",
                "Much of what goes in the general bin is recyclable, and landfill generates methane.",
                f"~{landfill_kg_waste * 12 / 52:.1f} kg/week of general waste",
                "Sort packaging, glass and paper into recycling",
                0.5 * landfill_kg_waste * (f_landfill - recycling),
                "easy",
                f"50% x {landfill_kg_waste:,.1f} kg/month x ({f_landfill:.4f} landfill - {recycling:.4f} recycling) kg CO2e/kg",
            )
        )
        if compost is not None and not profile.items_with_prefix("waste.composting"):
            recs.append(
                RecommendationCandidate(
                    "start_composting",
                    "waste",
                    "Start composting food scraps",
                    "Food waste in landfill decomposes into methane; composting avoids most of that.",
                    "No composting recorded",
                    "Compost food and garden waste (home bin or council collection)",
                    FOOD_WASTE_SHARE * landfill_kg_waste * (f_landfill - compost),
                    "easy",
                    f"30% food share (assumption) x {landfill_kg_waste:,.1f} kg/month x ({f_landfill:.4f} - {compost:.4f}) kg CO2e/kg",
                )
            )

    # --- Consumption ---------------------------------------------------------------------------
    _, clothing_usd, clothing_kg = _sum(profile, keys=("consumption.spend.clothing",))
    _, _, apparel_items_kg = _sum(profile, keys=("consumption.product.tshirt", "consumption.product.jeans"))
    apparel_kg = clothing_kg + apparel_items_kg
    if apparel_kg > 0:
        recs.append(
            RecommendationCandidate(
                "second_hand_clothing",
                "consumption",
                "Buy half your clothes second-hand",
                "Most of a garment's footprint comes from making it; reuse avoids that almost entirely.",
                f"{apparel_kg:,.1f} kg CO2e/month from new clothing",
                "Buy pre-owned or rent for half of clothing purchases",
                0.5 * apparel_kg * SECOND_HAND_SAVING,
                "easy",
                f"50% x {apparel_kg:,.2f} kg CO2e/month x 90% (assumed avoided production for second-hand)",
            )
        )
    _, _, device_kg = _sum(profile, keys=("consumption.product.smartphone", "consumption.product.laptop", "consumption.spend.electronics"))
    if device_kg > 0:
        recs.append(
            RecommendationCandidate(
                "extend_device_life",
                "consumption",
                "Keep devices one year longer",
                "Electronics' footprint is dominated by manufacturing, so longer lifetimes spread it thinner.",
                f"{device_kg:,.1f} kg CO2e/month from new electronics",
                "Extend replacement cycles from ~3 to ~4 years (repair, battery swaps)",
                0.25 * device_kg,
                "medium",
                f"{device_kg:,.2f} kg CO2e/month x (1 - 3/4): a 3-year cycle stretched to 4 years",
            )
        )

    out = []
    for rec in recs:
        if rec.estimated_monthly_reduction_kg < MIN_REDUCTION_KG:
            continue
        rec.estimated_monthly_reduction_kg = round(rec.estimated_monthly_reduction_kg, 2)
        rec.share_of_footprint_pct = round(100 * rec.estimated_monthly_reduction_kg / total, 1) if total else 0.0
        rec.priority_score = round(rec.estimated_monthly_reduction_kg * DIFFICULTY_WEIGHT[rec.difficulty], 3)
        out.append(rec)
    return sorted(out, key=lambda r: r.priority_score, reverse=True)
