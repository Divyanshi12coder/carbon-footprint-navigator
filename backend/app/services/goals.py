"""Goal progress tracking.

A goal is "reduce my monthly emissions (optionally for one category) by X% from a baseline".
Current monthly emissions are measured on the trailing 30 days — or, while the goal is younger
than 30 days, the post-start daily average scaled to a month.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import EmissionRecord, Goal, User

WINDOW_DAYS = 30
MIN_DAYS_FOR_STATUS = 7
DAYS_PER_MONTH = 30.4375


def monthly_emissions(db: Session, user_id, category: str | None, start: date, end: date) -> float:
    stmt = select(func.coalesce(func.sum(EmissionRecord.co2e_kg), 0.0)).where(
        EmissionRecord.user_id == user_id,
        EmissionRecord.organization_id.is_(None),
        EmissionRecord.occurred_on >= start,
        EmissionRecord.occurred_on <= end,
    )
    if category:
        stmt = stmt.where(EmissionRecord.category == category)
    return float(db.scalar(stmt) or 0.0)


def default_baseline(db: Session, user: User, category: str | None, today: date | None = None) -> float:
    today = today or date.today()
    return monthly_emissions(db, user.id, category, today - timedelta(days=WINDOW_DAYS - 1), today) * DAYS_PER_MONTH / WINDOW_DAYS


def evaluate(db: Session, goal: Goal, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    target = goal.baseline_monthly_kg * (1 - goal.target_reduction_pct / 100)
    elapsed = (today - goal.start_date).days + 1
    if elapsed <= 0:
        current, window_note = None, "Goal has not started yet."
    elif elapsed >= WINDOW_DAYS:
        current = default_baseline_window(db, goal, today)
        window_note = "Trailing 30 days, scaled to a month."
    else:
        kg = monthly_emissions(db, goal.user_id, goal.category, goal.start_date, today)
        current = kg / elapsed * DAYS_PER_MONTH
        window_note = f"Projected from {elapsed} day(s) since the goal started."

    needed = goal.baseline_monthly_kg - target
    if current is None or needed <= 0:
        progress = 0.0
    else:
        progress = max(0.0, min(100.0, 100 * (goal.baseline_monthly_kg - current) / needed))
    reduction_pct = (
        100 * (goal.baseline_monthly_kg - current) / goal.baseline_monthly_kg
        if current is not None and goal.baseline_monthly_kg > 0
        else None
    )
    days_left = (goal.deadline - today).days
    on_track = current is not None and current <= target

    if goal.status == "active" and current is not None and elapsed >= MIN_DAYS_FOR_STATUS:
        if on_track and elapsed >= WINDOW_DAYS:
            goal.status = "achieved"
            goal.achieved_at = datetime.now(UTC)
        elif today > goal.deadline:
            goal.status = "missed"

    return {
        "target_monthly_kg": round(target, 2),
        "current_monthly_kg": None if current is None else round(current, 2),
        "progress_pct": round(progress, 1),
        "reduction_achieved_pct": None if reduction_pct is None else round(reduction_pct, 1),
        "on_track": on_track,
        "days_elapsed": max(0, elapsed),
        "days_remaining": days_left,
        "measurement": window_note,
    }


def default_baseline_window(db: Session, goal: Goal, today: date) -> float:
    kg = monthly_emissions(db, goal.user_id, goal.category, today - timedelta(days=WINDOW_DAYS - 1), today)
    return kg * DAYS_PER_MONTH / WINDOW_DAYS
