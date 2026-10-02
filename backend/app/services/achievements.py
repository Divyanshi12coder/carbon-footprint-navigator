"""Achievement rules — each is a deterministic check against stored data."""

from collections.abc import Callable
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Achievement, Activity, EmissionRecord, Goal, User
from app.services.analytics import BENCHMARK

MONTHLY_BENCHMARK_KG = BENCHMARK["annual_kg"] / 12


def _activity_count(db: Session, user: User) -> int:
    return db.scalar(select(func.count(Activity.id)).where(Activity.user_id == user.id)) or 0


def _has_streak(db: Session, user: User, length: int = 7) -> bool:
    days = sorted(set(db.scalars(select(Activity.occurred_on).where(Activity.user_id == user.id))))
    run = 1
    for prev, cur in zip(days, days[1:], strict=False):
        run = run + 1 if cur - prev == timedelta(days=1) else 1
        if run >= length:
            return True
    return len(days) >= 1 and length <= 1


def _below_benchmark_month(db: Session, user: User) -> bool:
    today = date.today()
    start = today - timedelta(days=29)
    total, active_days = db.execute(
        select(func.coalesce(func.sum(EmissionRecord.co2e_kg), 0.0), func.count(func.distinct(EmissionRecord.occurred_on))).where(
            EmissionRecord.user_id == user.id,
            EmissionRecord.organization_id.is_(None),
            EmissionRecord.occurred_on >= start,
        )
    ).one()
    return active_days >= 20 and float(total) < MONTHLY_BENCHMARK_KG


RULES: list[tuple[str, str, str, Callable[[Session, User], bool]]] = [
    (
        "onboarded",
        "Baseline set",
        "Completed onboarding and estimated your starting footprint.",
        lambda db, u: u.onboarding_completed,
    ),
    ("first_activity", "First step", "Logged your first activity.", lambda db, u: _activity_count(db, u) >= 1),
    ("ten_activities", "Building the habit", "Logged 10 activities.", lambda db, u: _activity_count(db, u) >= 10),
    ("fifty_activities", "Data driven", "Logged 50 activities.", lambda db, u: _activity_count(db, u) >= 50),
    ("week_streak", "Seven-day streak", "Logged activities on 7 consecutive days.", _has_streak),
    (
        "first_goal",
        "Goal setter",
        "Created your first reduction goal.",
        lambda db, u: (db.scalar(select(func.count(Goal.id)).where(Goal.user_id == u.id)) or 0) >= 1,
    ),
    (
        "goal_achieved",
        "Target hit",
        "Achieved a reduction goal.",
        lambda db, u: (db.scalar(select(func.count(Goal.id)).where(Goal.user_id == u.id, Goal.status == "achieved")) or 0) >= 1,
    ),
    (
        "paris_aligned_month",
        "1.5°C pace",
        "A tracked 30 days below the 1.5°C-aligned lifestyle pace (208 kg/month).",
        _below_benchmark_month,
    ),
]


def check_and_award(db: Session, user: User) -> list[Achievement]:
    have = set(db.scalars(select(Achievement.code).where(Achievement.user_id == user.id)))
    new = []
    for code, title, description, rule in RULES:
        if code not in have and rule(db, user):
            achievement = Achievement(user_id=user.id, code=code, title=title, description=description)
            db.add(achievement)
            new.append(achievement)
    if new:
        db.commit()
    return new


def catalogue() -> list[dict[str, str]]:
    return [{"code": c, "title": t, "description": d} for c, t, d, _ in RULES]
