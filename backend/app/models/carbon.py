import uuid
from datetime import date

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

CATEGORIES = ("transport", "flights", "energy", "food", "waste", "consumption", "digital", "business", "other")
_CATEGORY_SQL = ", ".join(f"'{c}'" for c in CATEGORIES)


class EmissionFactor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A versioned, sourced emission factor (kg CO2e per unit).

    Factors are never edited in place: an update inserts a new version and deactivates the
    previous one, so every stored EmissionRecord keeps pointing at the exact factor used.
    """

    __tablename__ = "emission_factors"
    __table_args__ = (
        UniqueConstraint("key", "region", "version", name="uq_emission_factors_key_region_version"),
        CheckConstraint(f"category in ({_CATEGORY_SQL})", name="category_valid"),
        CheckConstraint("co2e_per_unit >= 0", name="co2e_non_negative"),
        CheckConstraint("quality in ('high', 'medium', 'low')", name="quality_valid"),
        Index("ix_emission_factors_lookup", "key", "region", "is_active"),
    )

    key: Mapped[str] = mapped_column(String(80), nullable=False)
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    region: Mapped[str] = mapped_column(String(8), default="GLOBAL", nullable=False)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)
    co2e_per_unit: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(300), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500))
    year: Mapped[int | None] = mapped_column(Integer)
    quality: Mapped[str] = mapped_column(String(8), default="medium", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    change_reason: Mapped[str | None] = mapped_column(String(300))


class Activity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Something the user did, exactly as they described it."""

    __tablename__ = "activities"
    __table_args__ = (
        CheckConstraint(f"category in ({_CATEGORY_SQL})", name="category_valid"),
        CheckConstraint("quantity >= 0", name="quantity_non_negative"),
        Index("ix_activities_user_date", "user_id", "occurred_on"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(48), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300))
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)
    # Activity-type specific inputs (fuel type, cabin class, origin/destination, ...).
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    source: Mapped[str] = mapped_column(String(24), default="manual", nullable=False)

    emission: Mapped["EmissionRecord"] = relationship(back_populates="activity", uselist=False, cascade="all, delete-orphan", lazy="joined")


class EmissionRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The calculated CO2e for an activity, with a full audit trail of how it was derived."""

    __tablename__ = "emission_records"
    __table_args__ = (
        CheckConstraint(f"category in ({_CATEGORY_SQL})", name="category_valid"),
        CheckConstraint("co2e_kg >= 0", name="co2e_non_negative"),
        CheckConstraint("data_quality in ('high', 'medium', 'low')", name="quality_valid"),
        Index("ix_emission_records_user_date", "user_id", "occurred_on"),
        Index("ix_emission_records_user_cat_date", "user_id", "category", "occurred_on"),
        Index("ix_emission_records_org_date", "organization_id", "occurred_on"),
    )

    activity_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("activities.id", ondelete="CASCADE"), unique=True, nullable=False)
    # Denormalised from the activity so analytics queries never need a join.
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("organizations.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(48), nullable=False)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)

    emission_factor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("emission_factors.id", ondelete="RESTRICT"))
    factor_key: Mapped[str] = mapped_column(String(80), nullable=False)
    factor_value: Mapped[float] = mapped_column(Float, nullable=False)
    factor_unit: Mapped[str] = mapped_column(String(24), nullable=False)
    factor_source: Mapped[str] = mapped_column(String(300), nullable=False)
    normalized_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    co2e_kg: Mapped[float] = mapped_column(Float, nullable=False)
    calculation_method: Mapped[str] = mapped_column(Text, nullable=False)
    data_quality: Mapped[str] = mapped_column(String(8), nullable=False)
    assumptions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    activity: Mapped[Activity] = relationship(back_populates="emission")
    factor: Mapped[EmissionFactor | None] = relationship(lazy="joined")
