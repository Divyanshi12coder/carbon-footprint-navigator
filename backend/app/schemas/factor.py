import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.carbon.units import _CONVERSIONS
from app.schemas.common import Category, ORMModel


class FactorOut(ORMModel):
    id: uuid.UUID
    key: str
    category: str
    name: str
    region: str
    unit: str
    co2e_per_unit: float
    source: str
    source_url: str | None
    year: int | None
    quality: str
    notes: str | None
    version: int
    is_active: bool
    change_reason: str | None
    updated_at: datetime


class FactorCreate(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9_]+(\.[a-z0-9_]+)+$", max_length=80)
    category: Category
    name: str = Field(min_length=2, max_length=160)
    region: str = Field(default="GLOBAL", max_length=8)
    unit: str
    co2e_per_unit: float = Field(ge=0, le=100000)
    source: str = Field(min_length=3, max_length=300)
    source_url: str | None = Field(default=None, max_length=500)
    year: int | None = Field(default=None, ge=1990, le=2100)
    quality: Literal["high", "medium", "low"] = "medium"
    notes: str | None = Field(default=None, max_length=2000)
    change_reason: str = Field(min_length=3, max_length=300)

    @field_validator("unit")
    @classmethod
    def known_unit(cls, v: str) -> str:
        if v not in _CONVERSIONS:
            raise ValueError(f"Unit must be one of {sorted(_CONVERSIONS)}.")
        return v

    @field_validator("region")
    @classmethod
    def upper_region(cls, v: str) -> str:
        return v.strip().upper()


class FactorUpdate(BaseModel):
    """An update creates a new version; the old version is deactivated but kept for traceability."""

    name: str | None = Field(default=None, min_length=2, max_length=160)
    co2e_per_unit: float | None = Field(default=None, ge=0, le=100000)
    source: str | None = Field(default=None, min_length=3, max_length=300)
    source_url: str | None = Field(default=None, max_length=500)
    year: int | None = Field(default=None, ge=1990, le=2100)
    quality: Literal["high", "medium", "low"] | None = None
    notes: str | None = Field(default=None, max_length=2000)
    change_reason: str = Field(min_length=3, max_length=300)
