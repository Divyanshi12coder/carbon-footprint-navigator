"""Glue between stored data and the ML layer (forecasting, anomaly detection, recommendations)."""

from dataclasses import asdict
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.carbon.behavior import BehaviorProfile, best_profile
from app.carbon.scenarios import FactorCache
from app.ml import anomaly_detection, forecasting, recommendations
from app.models import Prediction, Recommendation, User
from app.services.analytics import Scope, history_frame

MAX_STORED_PREDICTIONS = 20


def run_forecast(db: Session, user: User, horizon_days: int, persist: bool = True, today: date | None = None) -> forecasting.ForecastResult:
    frame = history_frame(db, Scope(user_id=user.id), today)
    if frame is None:
        result = forecasting.ForecastResult(status="insufficient_data", horizon_days=horizon_days)
        result.notes.append("No activities logged yet — add activities to enable forecasting.")
        return result
    result = forecasting.forecast(frame, horizon_days)
    if persist:
        db.add(
            Prediction(
                user_id=user.id,
                horizon_days=horizon_days,
                model_name=result.model_name or "none",
                status=result.status,
                predicted_total_kg=result.predicted_total_kg,
                lower_total_kg=result.lower_total_kg,
                upper_total_kg=result.upper_total_kg,
                metrics=result.metrics,
                points=result.points,
            )
        )
        db.flush()
        stale = db.scalars(
            select(Prediction.id)
            .where(Prediction.user_id == user.id)
            .order_by(Prediction.generated_at.desc())
            .offset(MAX_STORED_PREDICTIONS)
        ).all()
        if stale:
            db.execute(delete(Prediction).where(Prediction.id.in_(stale)))
        db.commit()
    return result


def run_anomaly_detection(db: Session, user: User, today: date | None = None) -> list[anomaly_detection.Anomaly]:
    frame = history_frame(db, Scope(user_id=user.id), today)
    if frame is None:
        return []
    return anomaly_detection.detect(frame)


def behaviour_profile(db: Session, user: User, today: date | None = None) -> BehaviorProfile:
    return best_profile(db, user.id, user.profile, today)


def refresh_recommendations(db: Session, user: User, today: date | None = None) -> list[Recommendation]:
    """Regenerate recommendations; keeps user-set status (accepted/dismissed/completed) per rec_key."""
    profile = behaviour_profile(db, user, today)
    region = user.profile.country if user.profile else None
    candidates = recommendations.generate(profile, FactorCache(db, region)) if profile.items else []
    existing = {r.rec_key: r for r in db.scalars(select(Recommendation).where(Recommendation.user_id == user.id))}
    seen = set()
    for cand in candidates:
        seen.add(cand.rec_key)
        fields = asdict(cand)
        fields["data_basis"] = profile.basis
        row = existing.get(cand.rec_key)
        if row is None:
            db.add(Recommendation(user_id=user.id, is_current=True, **fields))
        else:
            for k, v in fields.items():
                setattr(row, k, v)
            row.is_current = True
    for key, row in existing.items():
        if key not in seen:
            row.is_current = False  # behaviour no longer present; keep row for history
    db.commit()
    return list(
        db.scalars(
            select(Recommendation)
            .where(Recommendation.user_id == user.id, Recommendation.is_current.is_(True))
            .order_by(Recommendation.priority_score.desc())
        )
    )
