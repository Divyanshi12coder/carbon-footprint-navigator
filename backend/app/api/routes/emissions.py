"""Dashboard and analytics endpoints — all values aggregated from stored emission records."""

from datetime import date
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import Category, RangeKey
from app.services import analytics
from app.services.analytics import Scope

dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])
emissions_router = APIRouter(prefix="/emissions", tags=["emissions"])


def _range(range_key: str, start: date | None, end: date | None) -> tuple[date, date]:
    try:
        return analytics.resolve_range(range_key, start, end)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


@dashboard_router.get("/summary")
def summary(
    user: CurrentUser,
    db: DbSession,
    range: RangeKey = "30d",
    start: date | None = None,
    end: date | None = None,
) -> dict[str, Any]:
    s, e = _range(range, start, end)
    return analytics.dashboard_summary(db, Scope(user_id=user.id), s, e)


@emissions_router.get("/timeseries")
def timeseries(
    user: CurrentUser,
    db: DbSession,
    range: RangeKey = "90d",
    start: date | None = None,
    end: date | None = None,
    granularity: Literal["day", "week", "month"] = "day",
    category: Category | None = None,
) -> dict[str, Any]:
    s, e = _range(range, start, end)
    return analytics.timeseries(db, Scope(user_id=user.id), s, e, granularity, category)


@emissions_router.get("/breakdown")
def breakdown(
    user: CurrentUser, db: DbSession, range: RangeKey = "30d", start: date | None = None, end: date | None = None
) -> list[dict[str, Any]]:
    """Per activity type / factor breakdown (count, quantity, kg, share)."""
    s, e = _range(range, start, end)
    return analytics.by_activity(db, Scope(user_id=user.id), s, e)


@emissions_router.get("/monthly")
def monthly(user: CurrentUser, db: DbSession, months: Annotated[int, Query(ge=1, le=24)] = 12) -> list[dict[str, Any]]:
    return analytics.monthly_comparison(db, Scope(user_id=user.id), months)
