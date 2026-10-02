"""Activity catalogue and deterministic classification.

Each activity type declares its category, accepted units, the extra inputs it needs and how
those inputs resolve to an emission-factor key. The frontend renders its forms from this
catalogue (GET /api/activities/types), so the UI and the calculation rules never drift apart.
"""

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

FieldType = Literal["select", "number", "text", "boolean", "airport"]


@dataclass(frozen=True)
class Choice:
    value: str
    label: str


@dataclass(frozen=True)
class FieldSpec:
    name: str
    label: str
    type: FieldType
    required: bool = False
    default: Any = None
    choices: tuple[Choice, ...] = ()
    min: float | None = None
    max: float | None = None
    help: str | None = None


@dataclass(frozen=True)
class ActivityTypeSpec:
    key: str
    category: str
    label: str
    description: str
    quantity_label: str
    units: tuple[str, ...]
    fields: tuple[FieldSpec, ...] = ()
    resolve: Callable[[dict[str, Any]], str] = field(default=lambda d: "", repr=False)
    # "flight": quantity may be derived from origin/destination; "custom": user supplies the factor.
    mode: Literal["standard", "flight", "custom"] = "standard"

    def to_public(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("resolve", None)
        return data


def _choices(*pairs: tuple[str, str]) -> tuple[Choice, ...]:
    return tuple(Choice(v, label) for v, label in pairs)


FUEL_TYPES = _choices(
    ("petrol", "Petrol"),
    ("diesel", "Diesel"),
    ("hybrid", "Hybrid"),
    ("plugin_hybrid", "Plug-in hybrid"),
    ("electric", "Electric (BEV)"),
)
TRANSIT_MODES = _choices(
    ("bus", "Bus"),
    ("coach", "Coach"),
    ("rail", "Train"),
    ("metro_tram", "Metro / tram"),
    ("ferry", "Ferry"),
)
ACTIVE_MODES = _choices(("bicycle", "Bicycle"), ("walking", "Walking"))
CABIN_CLASSES = _choices(
    ("economy", "Economy"),
    ("premium_economy", "Premium economy"),
    ("business", "Business"),
    ("first", "First"),
)
ELECTRICITY_SOURCES = _choices(("grid", "Grid electricity"), ("renewable", "Renewable tariff / on-site solar"))
MEAL_TYPES = _choices(
    ("beef", "Beef"),
    ("lamb", "Lamb"),
    ("pork", "Pork"),
    ("chicken", "Chicken"),
    ("fish", "Fish"),
    ("dairy_heavy", "Dairy-heavy (cheese)"),
    ("vegetarian", "Vegetarian"),
    ("vegan", "Vegan"),
)
DIETS = _choices(
    ("meat_heavy", "Meat-heavy"),
    ("mixed", "Mixed (medium meat)"),
    ("low_meat", "Low meat"),
    ("pescatarian", "Pescatarian"),
    ("vegetarian", "Vegetarian"),
    ("vegan", "Vegan"),
)
WASTE_METHODS = _choices(
    ("landfill", "General waste (landfill)"),
    ("incineration", "General waste (incineration)"),
    ("recycling", "Recycling"),
    ("composting", "Composting"),
)
SPEND_CATEGORIES = _choices(
    ("clothing", "Clothing & footwear"),
    ("electronics", "Electronics"),
    ("household_goods", "Household goods"),
    ("furniture", "Furniture"),
)
PRODUCTS = _choices(
    ("smartphone", "Smartphone"),
    ("laptop", "Laptop"),
    ("tshirt", "T-shirt"),
    ("jeans", "Jeans"),
    ("television", "Television"),
)
CUSTOM_CATEGORIES = _choices(
    ("other", "Other"),
    ("transport", "Transport"),
    ("energy", "Energy"),
    ("food", "Food"),
    ("waste", "Waste"),
    ("consumption", "Consumption"),
    ("digital", "Digital"),
    ("business", "Business"),
)

DISTANCE_UNITS = ("km", "mi")

CATALOG: dict[str, ActivityTypeSpec] = {
    spec.key: spec
    for spec in [
        ActivityTypeSpec(
            "car",
            "transport",
            "Car journey",
            "Driving a private or company car.",
            "Distance",
            DISTANCE_UNITS,
            (
                FieldSpec("fuel_type", "Fuel type", "select", True, "petrol", FUEL_TYPES),
                FieldSpec(
                    "occupants",
                    "People in the car",
                    "number",
                    False,
                    1,
                    min=1,
                    max=9,
                    help="Emissions are shared equally between occupants.",
                ),
            ),
            resolve=lambda d: f"transport.car.{d['fuel_type']}",
        ),
        ActivityTypeSpec(
            "motorcycle",
            "transport",
            "Motorcycle ride",
            "Motorbike or scooter (fuel).",
            "Distance",
            DISTANCE_UNITS,
            resolve=lambda d: "transport.motorcycle",
        ),
        ActivityTypeSpec(
            "taxi",
            "transport",
            "Taxi / ride-hail",
            "Taxi or ride-hailing trip.",
            "Distance",
            DISTANCE_UNITS,
            resolve=lambda d: "transport.taxi",
        ),
        ActivityTypeSpec(
            "public_transport",
            "transport",
            "Public transport",
            "Bus, coach, train, metro or ferry.",
            "Distance",
            DISTANCE_UNITS,
            (FieldSpec("mode", "Mode", "select", True, "bus", TRANSIT_MODES),),
            resolve=lambda d: f"transport.{d['mode']}",
        ),
        ActivityTypeSpec(
            "active_travel",
            "transport",
            "Walking / cycling",
            "Zero-emission trips — tracked for completeness.",
            "Distance",
            DISTANCE_UNITS,
            (FieldSpec("mode", "Mode", "select", True, "bicycle", ACTIVE_MODES),),
            resolve=lambda d: f"transport.{d['mode']}",
        ),
        ActivityTypeSpec(
            "flight",
            "flights",
            "Flight",
            "Enter airports (IATA codes) or a distance.",
            "Distance (optional with airports)",
            DISTANCE_UNITS,
            (
                FieldSpec("origin", "From (IATA)", "airport", False, help="e.g. LHR"),
                FieldSpec("destination", "To (IATA)", "airport", False, help="e.g. JFK"),
                FieldSpec("cabin_class", "Cabin class", "select", True, "economy", CABIN_CLASSES),
                FieldSpec("passengers", "Passengers", "number", False, 1, min=1, max=9),
                FieldSpec("round_trip", "Return trip", "boolean", False, False),
            ),
            mode="flight",
        ),
        ActivityTypeSpec(
            "electricity",
            "energy",
            "Electricity use",
            "Metered electricity consumption.",
            "Energy",
            ("kWh", "MWh"),
            (FieldSpec("source", "Supply", "select", True, "grid", ELECTRICITY_SOURCES),),
            resolve=lambda d: f"energy.electricity.{d['source']}",
        ),
        ActivityTypeSpec(
            "natural_gas",
            "energy",
            "Natural gas",
            "Gas for heating or cooking.",
            "Energy",
            ("kWh", "therm", "m3", "MJ"),
            resolve=lambda d: "energy.natural_gas",
        ),
        ActivityTypeSpec("lpg", "energy", "LPG", "Bottled / bulk LPG.", "Volume", ("L", "gal"), resolve=lambda d: "energy.lpg"),
        ActivityTypeSpec(
            "heating_oil",
            "energy",
            "Heating oil",
            "Kerosene / burning oil.",
            "Volume",
            ("L", "gal"),
            resolve=lambda d: "energy.heating_oil",
        ),
        ActivityTypeSpec(
            "meal",
            "food",
            "Meals",
            "Individual meals by main ingredient.",
            "Servings",
            ("serving",),
            (FieldSpec("meal_type", "Meal type", "select", True, "chicken", MEAL_TYPES),),
            resolve=lambda d: f"food.meal.{d['meal_type']}",
        ),
        ActivityTypeSpec(
            "diet_day",
            "food",
            "Day of eating",
            "A whole day of food by overall diet pattern.",
            "Days",
            ("day",),
            (FieldSpec("diet", "Diet", "select", True, "mixed", DIETS),),
            resolve=lambda d: f"food.diet_day.{d['diet']}",
        ),
        ActivityTypeSpec(
            "waste",
            "waste",
            "Waste disposal",
            "Household or office waste by disposal route.",
            "Weight",
            ("kg", "lb"),
            (FieldSpec("method", "Disposal method", "select", True, "landfill", WASTE_METHODS),),
            resolve=lambda d: f"waste.{d['method']}",
        ),
        ActivityTypeSpec(
            "purchase",
            "consumption",
            "Purchase (by spend)",
            "Spend-based estimate for goods.",
            "Amount spent",
            ("USD",),
            (FieldSpec("item_category", "Category", "select", True, "clothing", SPEND_CATEGORIES),),
            resolve=lambda d: f"consumption.spend.{d['item_category']}",
        ),
        ActivityTypeSpec(
            "product",
            "consumption",
            "Product purchase",
            "Lifecycle footprint of specific products.",
            "Items",
            ("item",),
            (FieldSpec("product", "Product", "select", True, "smartphone", PRODUCTS),),
            resolve=lambda d: f"consumption.product.{d['product']}",
        ),
        ActivityTypeSpec(
            "streaming",
            "digital",
            "Video streaming",
            "Hours of video streaming.",
            "Duration",
            ("hour", "min"),
            resolve=lambda d: "digital.video_streaming",
        ),
        ActivityTypeSpec(
            "hotel_stay",
            "business",
            "Hotel stay",
            "Room-nights (business or leisure).",
            "Nights",
            ("room_night",),
            resolve=lambda d: "business.hotel_night",
        ),
        ActivityTypeSpec(
            "custom",
            "other",
            "Custom source",
            "Any other source with your own emission factor.",
            "Quantity",
            (),
            (
                FieldSpec("custom_category", "Category", "select", True, "other", CUSTOM_CATEGORIES),
                FieldSpec("factor_kg_per_unit", "Emission factor (kg CO₂e per unit)", "number", True, min=0, max=100000),
                FieldSpec("factor_source", "Factor source", "text", False, help="Where the factor comes from"),
            ),
            mode="custom",
        ),
    ]
}


class ActivityValidationError(ValueError):
    pass


def get_spec(activity_type: str) -> ActivityTypeSpec:
    spec = CATALOG.get(activity_type)
    if spec is None:
        raise ActivityValidationError(f"Unknown activity type '{activity_type}'.")
    return spec


def normalise_details(spec: ActivityTypeSpec, details: dict[str, Any]) -> dict[str, Any]:
    """Validate and fill defaults for activity-specific inputs. Unknown keys are dropped."""
    clean: dict[str, Any] = {}
    for f in spec.fields:
        value = details.get(f.name)
        if value in (None, ""):
            value = f.default
        if value is None:
            if f.required:
                raise ActivityValidationError(f"'{f.label}' is required for {spec.label}.")
            continue
        if f.type == "select":
            allowed = {c.value for c in f.choices}
            if value not in allowed:
                raise ActivityValidationError(f"'{value}' is not a valid {f.label.lower()}. Allowed: {sorted(allowed)}.")
        elif f.type == "number":
            try:
                value = float(value)
            except (TypeError, ValueError) as exc:
                raise ActivityValidationError(f"'{f.label}' must be a number.") from exc
            if (f.min is not None and value < f.min) or (f.max is not None and value > f.max):
                raise ActivityValidationError(f"'{f.label}' must be between {f.min} and {f.max}.")
        elif f.type == "boolean":
            value = bool(value) if not isinstance(value, str) else value.lower() in ("1", "true", "yes")
        elif f.type in ("text", "airport"):
            value = str(value).strip()[:200]
            if f.type == "airport":
                value = value.upper()
        clean[f.name] = value
    return clean


def category_for(spec: ActivityTypeSpec, details: dict[str, Any]) -> str:
    if spec.mode == "custom":
        return details.get("custom_category", "other")
    return spec.category
