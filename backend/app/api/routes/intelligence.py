"""ML-backed endpoints: insights, recommendations, forecasts, anomalies, scenarios."""

import uuid
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.carbon.scenarios import ScenarioLevers, simulate
from app.models import Insight, Recommendation
from app.schemas.engagement import (
    AnomalyOut,
    ForecastOut,
    InsightOut,
    RecommendationOut,
    RecommendationStatusIn,
    ScenarioIn,
    ScenarioOut,
)
from app.schemas.profile import BaselineItemOut, BaselineOut
from app.services import insights as insight_service
from app.services import ml_service

insights_router = APIRouter(prefix="/insights", tags=["insights"])
recommendations_router = APIRouter(prefix="/recommendations", tags=["recommendations"])
forecast_router = APIRouter(prefix="/forecast", tags=["forecast"])
anomalies_router = APIRouter(prefix="/anomalies", tags=["anomalies"])
scenarios_router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@insights_router.get("", response_model=list[InsightOut])
def list_insights(user: CurrentUser, db: DbSession) -> list[Insight]:
    rows = list(db.scalars(select(Insight).where(Insight.user_id == user.id).order_by(Insight.generated_at, Insight.id)))
    if not rows:
        rows = insight_service.refresh_insights(db, user)
    return rows


@insights_router.post("/refresh", response_model=list[InsightOut])
def refresh_insights(user: CurrentUser, db: DbSession) -> list[Insight]:
    return insight_service.refresh_insights(db, user)


@recommendations_router.get("", response_model=list[RecommendationOut])
def list_recommendations(user: CurrentUser, db: DbSession, include_dismissed: bool = False) -> list[Recommendation]:
    stmt = select(Recommendation).where(Recommendation.user_id == user.id, Recommendation.is_current.is_(True))
    if not include_dismissed:
        stmt = stmt.where(Recommendation.status != "dismissed")
    rows = list(db.scalars(stmt.order_by(Recommendation.priority_score.desc())))
    if not rows and not db.scalar(select(Recommendation.id).where(Recommendation.user_id == user.id)):
        rows = [r for r in ml_service.refresh_recommendations(db, user) if include_dismissed or r.status != "dismissed"]
    return rows


@recommendations_router.post("/refresh", response_model=list[RecommendationOut])
def refresh_recommendations(user: CurrentUser, db: DbSession) -> list[Recommendation]:
    return [r for r in ml_service.refresh_recommendations(db, user) if r.status != "dismissed"]


@recommendations_router.patch("/{rec_id}", response_model=RecommendationOut)
def set_recommendation_status(rec_id: uuid.UUID, payload: RecommendationStatusIn, user: CurrentUser, db: DbSession) -> Recommendation:
    rec = db.get(Recommendation, rec_id)
    if rec is None or rec.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recommendation not found")
    rec.status = payload.status
    db.commit()
    db.refresh(rec)
    return rec


@forecast_router.get("", response_model=ForecastOut)
def get_forecast(
    user: CurrentUser,
    db: DbSession,
    horizon: Annotated[int, Query(ge=7, le=90, description="Days ahead (UI uses 7, 30, 90)")] = 30,
) -> ForecastOut:
    result = ml_service.run_forecast(db, user, horizon)
    return ForecastOut(**asdict(result))


@anomalies_router.get("", response_model=list[AnomalyOut])
def get_anomalies(user: CurrentUser, db: DbSession) -> list[AnomalyOut]:
    return [AnomalyOut(**a.to_dict()) for a in ml_service.run_anomaly_detection(db, user)]


def _available_levers(profile) -> list[str]:
    keys = [i.factor_key for i in profile.items]
    has = lambda *prefixes: any(k.startswith(prefixes) for k in keys)  # noqa: E731
    levers = []
    if has("transport.car."):
        levers += ["car_reduction_pct", "ev_adoption_pct"]
    if has("flights."):
        levers.append("flight_reduction_pct")
    if has("energy.electricity."):
        levers += ["electricity_reduction_pct", "renewable_share_pct"]
    if has("energy.natural_gas", "energy.heating_oil", "energy.lpg"):
        levers.append("heating_reduction_pct")
    if has(
        "food.meal.beef",
        "food.meal.lamb",
        "food.meal.pork",
        "food.meal.chicken",
        "food.diet_day.meat_heavy",
        "food.diet_day.mixed",
        "food.diet_day.low_meat",
    ):
        levers.append("meat_reduction_pct")
    if has("waste.landfill"):
        levers.append("recycling_improvement_pct")
    return levers


@scenarios_router.get("/baseline", response_model=BaselineOut)
def scenario_baseline(user: CurrentUser, db: DbSession) -> BaselineOut:
    """The monthly behaviour profile scenarios are applied to (tracked data, or onboarding estimate)."""
    profile = ml_service.behaviour_profile(db, user)
    return BaselineOut(
        basis=profile.basis,
        monthly_total_kg=round(profile.monthly_total_kg, 2),
        annual_total_kg=round(profile.monthly_total_kg * 12, 1),
        by_category_monthly_kg={k: round(v, 2) for k, v in profile.by_category().items()},
        items=[
            BaselineItemOut(
                factor_key=i.factor_key,
                category=i.category,
                monthly_quantity=round(i.monthly_quantity, 3),
                unit=i.unit,
                factor_value=round(i.factor_value, 5),
                monthly_kg=round(i.monthly_kg, 3),
            )
            for i in sorted(profile.items, key=lambda i: -i.monthly_kg)
        ],
        assumptions=profile.assumptions,
    )


@scenarios_router.post("/simulate", response_model=ScenarioOut)
def simulate_scenario(payload: ScenarioIn, user: CurrentUser, db: DbSession) -> ScenarioOut:
    profile = ml_service.behaviour_profile(db, user)
    if not profile.items:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No data to simulate yet. Complete onboarding or log some activities first.",
        )
    result = simulate(db, profile, ScenarioLevers(**payload.model_dump()), user.profile.country if user.profile else None)
    return ScenarioOut(
        **{k: v for k, v in asdict(result).items()},
        current_annual_kg=round(result.current_annual_kg, 1),
        scenario_annual_kg=round(result.scenario_annual_kg, 1),
        available_levers=_available_levers(profile),
    )
