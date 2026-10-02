"""Goals, recommendations, insights, predictions and assistant conversations."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class Goal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A reduction target expressed against a monthly (30-day) baseline."""

    __tablename__ = "goals"
    __table_args__ = (
        CheckConstraint("target_reduction_pct > 0 and target_reduction_pct <= 100", name="reduction_range"),
        CheckConstraint("baseline_monthly_kg >= 0", name="baseline_non_negative"),
        CheckConstraint("status in ('active', 'achieved', 'missed', 'archived')", name="status_valid"),
        Index("ix_goals_user_status", "user_id", "status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str | None] = mapped_column(String(24))  # None = all categories
    baseline_monthly_kg: Mapped[float] = mapped_column(Float, nullable=False)
    target_reduction_pct: Mapped[float] = mapped_column(Float, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    deadline: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    achieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Recommendation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        UniqueConstraint("user_id", "rec_key", name="uq_recommendations_user_key"),
        CheckConstraint("difficulty in ('easy', 'medium', 'hard')", name="difficulty_valid"),
        CheckConstraint("status in ('open', 'accepted', 'dismissed', 'completed')", name="status_valid"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    rec_key: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    current_behavior: Mapped[str] = mapped_column(String(300), nullable=False)
    suggested_action: Mapped[str] = mapped_column(String(300), nullable=False)
    estimated_monthly_reduction_kg: Mapped[float] = mapped_column(Float, nullable=False)
    share_of_footprint_pct: Mapped[float] = mapped_column(Float, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(8), nullable=False)
    calculation_basis: Mapped[str] = mapped_column(Text, nullable=False)
    data_basis: Mapped[str] = mapped_column(String(24), nullable=False)  # tracked_activities | onboarding_profile
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_current: Mapped[bool] = mapped_column(default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="open", nullable=False)


class Insight(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "insights"
    __table_args__ = (
        CheckConstraint("severity in ('positive', 'info', 'warning')", name="severity_valid"),
        Index("ix_insights_user_generated", "user_id", "generated_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    insight_type: Mapped[str] = mapped_column(String(48), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(24))
    metric_value: Mapped[float | None] = mapped_column(Float)
    data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Prediction(UUIDPrimaryKeyMixin, Base):
    """A persisted forecast run — model, metrics and points — for auditability."""

    __tablename__ = "predictions"
    __table_args__ = (Index("ix_predictions_user_generated", "user_id", "generated_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    horizon_days: Mapped[int] = mapped_column(nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    predicted_total_kg: Mapped[float | None] = mapped_column(Float)
    lower_total_kg: Mapped[float | None] = mapped_column(Float)
    upper_total_kg: Mapped[float | None] = mapped_column(Float)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    points: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role in ('user', 'assistant')", name="role_valid"),
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # "llm" (real model call) or "demo" (deterministic, data-grounded template). Null for user turns.
    mode: Mapped[str | None] = mapped_column(String(8))
    model: Mapped[str | None] = mapped_column(String(64))
    # Facts given to the model and the result of numeric validation, for transparency.
    context_used: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    validation: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
