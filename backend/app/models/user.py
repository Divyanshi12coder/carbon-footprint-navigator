import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(120))
    country: Mapped[str | None] = mapped_column(String(2))
    employee_count: Mapped[int | None] = mapped_column(Integer)
    # Members join with this code; it is only shown to the owner.
    join_code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL", use_alter=True))

    members: Mapped[list["User"]] = relationship(back_populates="organization", foreign_keys="User.organization_id")


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role in ('user', 'admin')", name="role_valid"),
        CheckConstraint("org_role is null or org_role in ('owner', 'member')", name="org_role_valid"),
    )

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Incremented on logout / password change to revoke previously issued JWTs.
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    organization_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("organizations.id", ondelete="SET NULL"), index=True)
    org_role: Mapped[str | None] = mapped_column(String(16))

    organization: Mapped[Organization | None] = relationship(back_populates="members", foreign_keys=[organization_id])
    profile: Mapped["UserProfile | None"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    preferences: Mapped["UserPreference | None"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserProfile(TimestampMixin, Base):
    """Onboarding answers. All behavioural fields are optional — users may skip them."""

    __tablename__ = "user_profiles"
    __table_args__ = (
        CheckConstraint("household_size is null or household_size between 1 and 20", name="household_size_range"),
        CheckConstraint(
            "renewable_share_pct is null or (renewable_share_pct >= 0 and renewable_share_pct <= 100)",
            name="renewable_share_range",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    country: Mapped[str | None] = mapped_column(String(2))  # ISO 3166-1 alpha-2
    region: Mapped[str | None] = mapped_column(String(120))
    household_size: Mapped[int | None] = mapped_column(Integer)

    primary_transport: Mapped[str | None] = mapped_column(String(32))  # car | public_transport | active | mixed
    vehicle_type: Mapped[str | None] = mapped_column(String(32))  # petrol | diesel | hybrid | plugin_hybrid | electric | none
    weekly_car_km: Mapped[float | None] = mapped_column(Float)
    weekly_public_transport_km: Mapped[float | None] = mapped_column(Float)
    short_haul_flights_per_year: Mapped[int | None] = mapped_column(Integer)
    long_haul_flights_per_year: Mapped[int | None] = mapped_column(Integer)

    monthly_electricity_kwh: Mapped[float | None] = mapped_column(Float)
    renewable_share_pct: Mapped[float | None] = mapped_column(Float)
    heating_fuel: Mapped[str | None] = mapped_column(String(32))  # natural_gas | heating_oil | lpg | electric | none
    monthly_heating_kwh: Mapped[float | None] = mapped_column(Float)

    diet_type: Mapped[str | None] = mapped_column(String(32))  # meat_heavy | mixed | low_meat | pescatarian | vegetarian | vegan
    shopping_level: Mapped[str | None] = mapped_column(String(16))  # low | medium | high
    monthly_clothing_spend_usd: Mapped[float | None] = mapped_column(Float)
    monthly_electronics_spend_usd: Mapped[float | None] = mapped_column(Float)

    weekly_waste_kg: Mapped[float | None] = mapped_column(Float)
    recycling_level: Mapped[str | None] = mapped_column(String(16))  # none | some | most
    composts: Mapped[bool | None] = mapped_column(Boolean)

    user: Mapped[User] = relationship(back_populates="profile")


class UserPreference(TimestampMixin, Base):
    __tablename__ = "user_preferences"
    __table_args__ = (
        CheckConstraint("distance_unit in ('km', 'mi')", name="distance_unit_valid"),
        CheckConstraint("default_range in ('7d', '30d', '90d', '180d', '365d')", name="default_range_valid"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    distance_unit: Mapped[str] = mapped_column(String(4), default="km", nullable=False)
    default_range: Mapped[str] = mapped_column(String(8), default="30d", nullable=False)
    monthly_budget_kg: Mapped[float | None] = mapped_column(Float)

    user: Mapped[User] = relationship(back_populates="preferences")


class Achievement(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "achievements"
    # Achievements are awarded once per user.
    __table_args__ = (UniqueConstraint("user_id", "code", name="uq_achievements_user_code"),)

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(48), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    achieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
