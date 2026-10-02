from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import COUNTRY_RE, ORMModel


class ProfileIn(BaseModel):
    """All fields optional — onboarding questions can be skipped."""

    country: str | None = Field(default=None, description="ISO 3166-1 alpha-2, e.g. GB, US, IN")
    region: str | None = Field(default=None, max_length=120)
    household_size: int | None = Field(default=None, ge=1, le=20)
    primary_transport: Literal["car", "public_transport", "active", "mixed"] | None = None
    vehicle_type: Literal["petrol", "diesel", "hybrid", "plugin_hybrid", "electric", "none"] | None = None
    weekly_car_km: float | None = Field(default=None, ge=0, le=10000)
    weekly_public_transport_km: float | None = Field(default=None, ge=0, le=10000)
    short_haul_flights_per_year: int | None = Field(default=None, ge=0, le=200)
    long_haul_flights_per_year: int | None = Field(default=None, ge=0, le=100)
    monthly_electricity_kwh: float | None = Field(default=None, ge=0, le=100000)
    renewable_share_pct: float | None = Field(default=None, ge=0, le=100)
    heating_fuel: Literal["natural_gas", "heating_oil", "lpg", "electric", "none"] | None = None
    monthly_heating_kwh: float | None = Field(default=None, ge=0, le=100000)
    diet_type: Literal["meat_heavy", "mixed", "low_meat", "pescatarian", "vegetarian", "vegan"] | None = None
    shopping_level: Literal["low", "medium", "high"] | None = None
    monthly_clothing_spend_usd: float | None = Field(default=None, ge=0, le=100000)
    monthly_electronics_spend_usd: float | None = Field(default=None, ge=0, le=100000)
    weekly_waste_kg: float | None = Field(default=None, ge=0, le=1000)
    recycling_level: Literal["none", "some", "most"] | None = None
    composts: bool | None = None

    @field_validator("country")
    @classmethod
    def upper_country(cls, v: str | None) -> str | None:
        if v in (None, ""):
            return None
        v = v.strip().upper()
        if not COUNTRY_RE.match(v):
            raise ValueError("Country must be a two-letter ISO code, e.g. GB.")
        return v


class ProfileOut(ProfileIn, ORMModel):
    pass


class OnboardingIn(ProfileIn):
    organization_name: str | None = Field(default=None, max_length=160)
    organization_industry: str | None = Field(default=None, max_length=120)
    organization_employee_count: int | None = Field(default=None, ge=1, le=10_000_000)


class PreferencesIn(BaseModel):
    distance_unit: Literal["km", "mi"] | None = None
    default_range: Literal["7d", "30d", "90d", "180d", "365d"] | None = None
    monthly_budget_kg: float | None = Field(default=None, ge=0, le=100000)


class PreferencesOut(ORMModel):
    distance_unit: str
    default_range: str
    monthly_budget_kg: float | None = None


class BaselineItemOut(BaseModel):
    factor_key: str
    category: str
    monthly_quantity: float
    unit: str
    factor_value: float
    monthly_kg: float


class BaselineOut(BaseModel):
    basis: str
    monthly_total_kg: float
    annual_total_kg: float
    by_category_monthly_kg: dict[str, float]
    items: list[BaselineItemOut]
    assumptions: list[str]
