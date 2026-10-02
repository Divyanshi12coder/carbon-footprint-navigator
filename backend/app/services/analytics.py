"""Emission analytics: all numbers are aggregated in SQL from stored EmissionRecords."""

import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy import ColumnElement, and_, func, select
from sqlalchemy.orm import Session

from app.ml.feature_engineering import DailyFrame, build_daily_frame, rolling_mean
from app.models import EmissionRecord

RANGE_DAYS = {"7d": 7, "30d": 30, "90d": 90, "180d": 180, "365d": 365}
WEEKLY_GRANULARITY_THRESHOLD_DAYS = 92
BENCHMARK = {
    "label": "1.5°C-aligned lifestyle footprint target for 2030",
    "annual_kg": 2500.0,
    "source": "Hot or Cool Institute (2021), 1.5-Degree Lifestyles",
    "source_url": "https://hotorcool.org/1-5-degree-lifestyles-report/",
}


@dataclass(frozen=True)
class Scope:
    """Personal data (user_id) or an organisation's pooled data (organization_id)."""

    user_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None

    def condition(self) -> ColumnElement[bool]:
        if self.organization_id is not None:
            return EmissionRecord.organization_id == self.organization_id
        if self.user_id is None:
            raise ValueError("Scope requires a user or an organization")
        return and_(EmissionRecord.user_id == self.user_id, EmissionRecord.organization_id.is_(None))


def resolve_range(range_key: str, start: date | None, end: date | None, today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    if range_key == "custom":
        if not start or not end:
            raise ValueError("Custom ranges need both start and end dates.")
        if start > end:
            raise ValueError("Start date must be on or before end date.")
        if (end - start).days > 3 * 366:
            raise ValueError("Custom ranges are limited to three years.")
        return start, end
    if range_key not in RANGE_DAYS:
        raise ValueError(f"Unknown range '{range_key}'.")
    return today - timedelta(days=RANGE_DAYS[range_key] - 1), today


def daily_category_rows(db: Session, scope: Scope, start: date, end: date) -> list[tuple[date, str, float]]:
    rows = db.execute(
        select(EmissionRecord.occurred_on, EmissionRecord.category, func.sum(EmissionRecord.co2e_kg))
        .where(scope.condition(), EmissionRecord.occurred_on >= start, EmissionRecord.occurred_on <= end)
        .group_by(EmissionRecord.occurred_on, EmissionRecord.category)
    ).all()
    return [(d, c, float(kg or 0)) for d, c, kg in rows]


def first_record_date(db: Session, scope: Scope) -> date | None:
    return db.scalar(select(func.min(EmissionRecord.occurred_on)).where(scope.condition()))


def history_frame(db: Session, scope: Scope, today: date | None = None, max_days: int = 365) -> DailyFrame | None:
    today = today or date.today()
    first = first_record_date(db, scope)
    if first is None:
        return None
    start = max(first, today - timedelta(days=max_days - 1))
    return build_daily_frame(daily_category_rows(db, scope, start, today), start, today)


def _sum_range(db: Session, scope: Scope, start: date, end: date) -> float:
    value = db.scalar(
        select(func.coalesce(func.sum(EmissionRecord.co2e_kg), 0.0)).where(
            scope.condition(), EmissionRecord.occurred_on >= start, EmissionRecord.occurred_on <= end
        )
    )
    return float(value or 0)


def _pct_change(current: float, previous: float) -> float | None:
    if previous <= 0:
        return None
    return round(100 * (current - previous) / previous, 1)


def _category_totals(rows: list[tuple[date, str, float]]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for _, category, kg in rows:
        totals[category] = totals.get(category, 0.0) + kg
    return totals


def build_timeline(frame: DailyFrame, granularity: str) -> list[dict[str, Any]]:
    categories = sorted(frame.by_category)
    points: list[dict[str, Any]] = []
    if granularity == "day":
        roll = rolling_mean(frame.total, 7)
        for i, d in enumerate(frame.dates):
            point: dict[str, Any] = {
                "period_start": d.isoformat(),
                "total_kg": round(float(frame.total[i]), 3),
                "rolling_7d_kg": round(float(roll[i]), 3),
            }
            point.update({c: round(float(frame.by_category[c][i]), 3) for c in categories})
            points.append(point)
        return points
    step = 7 if granularity == "week" else 30
    for lo in range(0, frame.n, step):
        hi = min(frame.n, lo + step)
        point = {
            "period_start": frame.dates[lo].isoformat(),
            "period_end": frame.dates[hi - 1].isoformat(),
            "total_kg": round(float(frame.total[lo:hi].sum()), 3),
        }
        point.update({c: round(float(frame.by_category[c][lo:hi].sum()), 3) for c in categories})
        points.append(point)
    return points


def dashboard_summary(db: Session, scope: Scope, start: date, end: date, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    days = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)

    rows = daily_category_rows(db, scope, start, end)
    prev_rows = daily_category_rows(db, scope, prev_start, prev_end)
    frame = build_daily_frame(rows, start, end)
    total = float(frame.total.sum())
    prev_total = sum(kg for _, _, kg in prev_rows)

    cats = _category_totals(rows)
    prev_cats = _category_totals(prev_rows)
    categories = [
        {
            "category": c,
            "kg": round(cats.get(c, 0.0), 3),
            "share_pct": round(100 * cats.get(c, 0.0) / total, 1) if total else 0.0,
            "previous_kg": round(prev_cats.get(c, 0.0), 3),
            "change_pct": _pct_change(cats.get(c, 0.0), prev_cats.get(c, 0.0)),
        }
        for c in sorted(set(cats) | set(prev_cats), key=lambda k: cats.get(k, 0.0), reverse=True)
    ]

    top_types = db.execute(
        select(EmissionRecord.activity_type, func.count(EmissionRecord.id), func.sum(EmissionRecord.co2e_kg))
        .where(scope.condition(), EmissionRecord.occurred_on >= start, EmissionRecord.occurred_on <= end)
        .group_by(EmissionRecord.activity_type)
        .order_by(func.sum(EmissionRecord.co2e_kg).desc())
        .limit(6)
    ).all()
    quality = db.execute(
        select(EmissionRecord.data_quality, func.count(EmissionRecord.id))
        .where(scope.condition(), EmissionRecord.occurred_on >= start, EmissionRecord.occurred_on <= end)
        .group_by(EmissionRecord.data_quality)
    ).all()
    activity_count = sum(int(n) for _, n in quality)

    daily_avg = total / days
    granularity = "day" if days <= WEEKLY_GRANULARITY_THRESHOLD_DAYS else "week"
    return {
        "range": {"start": start.isoformat(), "end": end.isoformat(), "days": days},
        "previous_range": {"start": prev_start.isoformat(), "end": prev_end.isoformat()},
        "totals": {
            "total_kg": round(total, 3),
            "previous_total_kg": round(prev_total, 3),
            "change_pct": _pct_change(total, prev_total),
            "daily_average_kg": round(daily_avg, 3),
            "weekly_average_kg": round(daily_avg * 7, 3),
            "monthly_equivalent_kg": round(daily_avg * 30.4375, 3),
            "annualized_kg": round(daily_avg * 365.25, 1),
            "activity_count": activity_count,
        },
        "snapshot": {
            "today_kg": round(_sum_range(db, scope, today, today), 3),
            "last_7_days_kg": round(_sum_range(db, scope, today - timedelta(days=6), today), 3),
            "last_30_days_kg": round(_sum_range(db, scope, today - timedelta(days=29), today), 3),
            "month_to_date_kg": round(_sum_range(db, scope, today.replace(day=1), today), 3),
        },
        "categories": categories,
        "granularity": granularity,
        "timeline": build_timeline(frame, granularity),
        "top_activity_types": [{"activity_type": t, "count": int(n), "kg": round(float(kg or 0), 3)} for t, n, kg in top_types],
        "data_quality": {q: int(n) for q, n in quality},
        "benchmark": BENCHMARK,
    }


def timeseries(db: Session, scope: Scope, start: date, end: date, granularity: str, category: str | None) -> dict[str, Any]:
    rows = daily_category_rows(db, scope, start, end)
    if category:
        rows = [r for r in rows if r[1] == category]
    frame = build_daily_frame(rows, start, end)
    return {"granularity": granularity, "category": category, "points": build_timeline(frame, granularity)}


def monthly_comparison(db: Session, scope: Scope, months: int, today: date | None = None) -> list[dict[str, Any]]:
    today = today or date.today()
    first_month = today.replace(day=1)
    for _ in range(months - 1):
        first_month = (first_month - timedelta(days=1)).replace(day=1)
    rows = daily_category_rows(db, scope, first_month, today)
    buckets: dict[str, dict[str, float]] = {}
    cursor = first_month
    while cursor <= today:
        buckets[cursor.strftime("%Y-%m")] = {}
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
    for d, category, kg in rows:
        bucket = buckets[d.strftime("%Y-%m")]
        bucket[category] = bucket.get(category, 0.0) + kg
    out = []
    for month, cats in buckets.items():
        out.append({"month": month, "total_kg": round(sum(cats.values()), 3), **{c: round(v, 3) for c, v in cats.items()}})
    return out


def by_activity(db: Session, scope: Scope, start: date, end: date) -> list[dict[str, Any]]:
    rows = db.execute(
        select(
            EmissionRecord.activity_type,
            EmissionRecord.factor_key,
            EmissionRecord.category,
            EmissionRecord.factor_unit,
            func.count(EmissionRecord.id),
            func.sum(EmissionRecord.normalized_quantity),
            func.sum(EmissionRecord.co2e_kg),
        )
        .where(scope.condition(), EmissionRecord.occurred_on >= start, EmissionRecord.occurred_on <= end)
        .group_by(EmissionRecord.activity_type, EmissionRecord.factor_key, EmissionRecord.category, EmissionRecord.factor_unit)
        .order_by(func.sum(EmissionRecord.co2e_kg).desc())
    ).all()
    total = sum(float(r[6] or 0) for r in rows)
    return [
        {
            "activity_type": t,
            "factor_key": key,
            "category": cat,
            "unit": unit,
            "count": int(n),
            "quantity": round(float(qty or 0), 3),
            "kg": round(float(kg or 0), 3),
            "avg_kg_per_activity": round(float(kg or 0) / n, 3) if n else 0.0,
            "share_pct": round(100 * float(kg or 0) / total, 1) if total else 0.0,
        }
        for t, key, cat, unit, n, qty, kg in rows
    ]
