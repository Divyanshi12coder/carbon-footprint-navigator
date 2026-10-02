import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import Category, ORMModel


class GoalIn(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    category: Category | None = None
    target_reduction_pct: float = Field(gt=0, le=100)
    baseline_monthly_kg: float | None = Field(
        default=None, ge=0, le=1_000_000, description="Defaults to your last 30 days of tracked emissions."
    )
    start_date: date | None = None
    deadline: date

    @model_validator(mode="after")
    def check_dates(self) -> "GoalIn":
        start = self.start_date or date.today()
        if self.deadline <= start:
            raise ValueError("Deadline must be after the start date.")
        return self


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=160)
    deadline: date | None = None
    status: Literal["active", "archived"] | None = None


class GoalProgress(BaseModel):
    target_monthly_kg: float
    current_monthly_kg: float | None
    progress_pct: float
    reduction_achieved_pct: float | None
    on_track: bool
    days_elapsed: int
    days_remaining: int
    measurement: str


class GoalOut(ORMModel):
    id: uuid.UUID
    title: str
    category: str | None
    baseline_monthly_kg: float
    target_reduction_pct: float
    start_date: date
    deadline: date
    status: str
    achieved_at: datetime | None
    created_at: datetime
    progress: GoalProgress


class RecommendationOut(ORMModel):
    id: uuid.UUID
    rec_key: str
    category: str
    title: str
    reason: str
    current_behavior: str
    suggested_action: str
    estimated_monthly_reduction_kg: float
    share_of_footprint_pct: float
    difficulty: str
    calculation_basis: str
    data_basis: str
    priority_score: float
    status: str
    updated_at: datetime


class RecommendationStatusIn(BaseModel):
    status: Literal["open", "accepted", "dismissed", "completed"]


class InsightOut(ORMModel):
    id: uuid.UUID
    insight_type: str
    severity: str
    title: str
    body: str
    category: str | None
    metric_value: float | None
    data: dict[str, Any]
    generated_at: datetime


class AchievementOut(BaseModel):
    code: str
    title: str
    description: str
    achieved: bool
    achieved_at: datetime | None = None


class ScenarioIn(BaseModel):
    car_reduction_pct: float = Field(default=0, ge=0, le=100)
    ev_adoption_pct: float = Field(default=0, ge=0, le=100)
    flight_reduction_pct: float = Field(default=0, ge=0, le=100)
    electricity_reduction_pct: float = Field(default=0, ge=0, le=100)
    renewable_share_pct: float = Field(default=0, ge=0, le=100)
    heating_reduction_pct: float = Field(default=0, ge=0, le=100)
    meat_reduction_pct: float = Field(default=0, ge=0, le=100)
    recycling_improvement_pct: float = Field(default=0, ge=0, le=100)


class LeverEffect(BaseModel):
    lever: str
    label: str
    value: float
    monthly_reduction_kg: float


class ScenarioOut(BaseModel):
    basis: str
    current_monthly_kg: float
    scenario_monthly_kg: float
    reduction_monthly_kg: float
    reduction_pct: float
    current_annual_kg: float
    scenario_annual_kg: float
    current_by_category: dict[str, float]
    scenario_by_category: dict[str, float]
    lever_effects: list[LeverEffect]
    assumptions: list[str]
    available_levers: list[str]


class ForecastPoint(BaseModel):
    date: str
    predicted_kg: float
    lower_kg: float
    upper_kg: float


class HistoryPoint(BaseModel):
    date: str
    actual_kg: float
    rolling_7d_kg: float


class ForecastOut(BaseModel):
    status: str
    horizon_days: int
    model_name: str | None
    points: list[ForecastPoint]
    history: list[HistoryPoint]
    predicted_total_kg: float | None
    lower_total_kg: float | None
    upper_total_kg: float | None
    recent_total_kg: float | None
    metrics: dict[str, Any]
    notes: list[str]


class AnomalyOut(BaseModel):
    method: str
    category: str | None
    date: str | None
    period_start: str | None
    period_end: str | None
    observed_kg: float
    expected_kg: float
    pct_above: float
    score: float
    message: str


class ConversationIn(BaseModel):
    title: str | None = Field(default=None, max_length=160)


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


class MessageOut(ORMModel):
    id: uuid.UUID
    role: str
    content: str
    mode: str | None
    model: str | None
    validation: dict[str, Any]
    context_used: dict[str, Any]
    created_at: datetime


class ConversationOut(ORMModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]


class OrganizationIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    industry: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, pattern=r"^[A-Za-z]{2}$")
    employee_count: int | None = Field(default=None, ge=1, le=10_000_000)


class JoinOrganizationIn(BaseModel):
    join_code: str = Field(min_length=6, max_length=16)


class OrganizationOut(ORMModel):
    id: uuid.UUID
    name: str
    industry: str | None
    country: str | None
    employee_count: int | None
    join_code: str | None = None
    created_at: datetime
