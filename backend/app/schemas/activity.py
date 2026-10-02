import uuid
from datetime import date, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel

MAX_PAST_YEARS = 5


def _check_date(v: date) -> date:
    today = date.today()
    if v > today + timedelta(days=1):
        raise ValueError("Activities cannot be dated in the future.")
    if v < today - timedelta(days=366 * MAX_PAST_YEARS):
        raise ValueError(f"Activities older than {MAX_PAST_YEARS} years are not supported.")
    return v


class ActivityIn(BaseModel):
    activity_type: str = Field(max_length=48)
    quantity: float | None = Field(default=None, ge=0, le=1_000_000)
    unit: str | None = Field(default=None, max_length=24)
    occurred_on: date
    details: dict[str, Any] = Field(default_factory=dict)
    description: str | None = Field(default=None, max_length=300)
    for_organization: bool = False

    @field_validator("occurred_on")
    @classmethod
    def valid_date(cls, v: date) -> date:
        return _check_date(v)


class ActivityUpdate(BaseModel):
    activity_type: str | None = Field(default=None, max_length=48)
    quantity: float | None = Field(default=None, ge=0, le=1_000_000)
    unit: str | None = Field(default=None, max_length=24)
    occurred_on: date | None = None
    details: dict[str, Any] | None = None
    description: str | None = Field(default=None, max_length=300)
    for_organization: bool | None = None

    @field_validator("occurred_on")
    @classmethod
    def valid_date(cls, v: date | None) -> date | None:
        return None if v is None else _check_date(v)


class PreviewIn(BaseModel):
    activity_type: str = Field(max_length=48)
    quantity: float | None = Field(default=None, ge=0, le=1_000_000)
    unit: str | None = Field(default=None, max_length=24)
    details: dict[str, Any] = Field(default_factory=dict)


class EmissionOut(ORMModel):
    id: uuid.UUID
    co2e_kg: float
    factor_key: str
    factor_value: float
    factor_unit: str
    factor_source: str
    emission_factor_id: uuid.UUID | None
    normalized_quantity: float
    calculation_method: str
    data_quality: str
    assumptions: list[str]


class ActivityOut(ORMModel):
    id: uuid.UUID
    category: str
    activity_type: str
    description: str | None
    quantity: float
    unit: str
    occurred_on: date
    details: dict[str, Any]
    source: str
    organization_id: uuid.UUID | None
    created_at: datetime
    emission: EmissionOut


class PreviewOut(BaseModel):
    category: str
    co2e_kg: float
    factor_key: str
    factor_value: float
    factor_unit: str
    factor_source: str
    factor_region: str
    normalized_quantity: float
    calculation_method: str
    data_quality: str
    assumptions: list[str]
    details: dict[str, Any]
