import math
import uuid
from datetime import date
from typing import Annotated, Any, Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Response, status

from app.api.deps import CurrentUser, DbSession
from app.carbon.catalog import CATALOG
from app.carbon.engine import CalculationError, calculate
from app.carbon.flights import airports
from app.schemas.activity import ActivityIn, ActivityOut, ActivityUpdate, PreviewIn, PreviewOut
from app.schemas.common import Category, Page
from app.services import activities as service
from app.services.pipeline import refresh_user_analytics

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("/types")
def activity_types() -> list[dict[str, Any]]:
    """The activity catalogue that drives the tracker form (fields, units, choices)."""
    return [spec.to_public() for spec in CATALOG.values()]


@router.get("/airports")
def airport_list() -> list[dict[str, str]]:
    return [{"iata": a.iata, "name": a.name, "city": a.city, "country": a.country} for a in airports().values()]


@router.post("/preview", response_model=PreviewOut)
def preview(payload: PreviewIn, user: CurrentUser, db: DbSession) -> PreviewOut:
    """Calculate CO2e without saving — powers the live estimate in the tracker form."""
    try:
        r = calculate(db, payload.activity_type, payload.quantity, payload.unit, payload.details, service.user_region(user))
    except CalculationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return PreviewOut(
        category=r.category,
        co2e_kg=round(r.co2e_kg, 4),
        factor_key=r.factor_key,
        factor_value=r.factor_value,
        factor_unit=r.factor_unit,
        factor_source=r.factor_source,
        factor_region=r.factor_region,
        normalized_quantity=round(r.normalized_quantity, 4),
        calculation_method=r.calculation_method,
        data_quality=r.data_quality,
        assumptions=r.assumptions,
        details=r.details,
    )


@router.get("", response_model=Page[ActivityOut])
def list_activities(
    user: CurrentUser,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    category: Category | None = None,
    activity_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    scope: Literal["personal", "organization", "all"] = "personal",
    sort: Literal["occurred_on", "created_at", "co2e_kg", "category"] = "occurred_on",
    order: Literal["asc", "desc"] = "desc",
) -> Page[ActivityOut]:
    items, total = service.list_activities(
        db,
        user,
        page=page,
        page_size=page_size,
        category=category,
        activity_type=activity_type,
        date_from=date_from,
        date_to=date_to,
        search=search,
        scope=scope,
        sort=sort,
        order=order,
    )
    return Page(items=items, total=total, page=page, page_size=page_size, pages=max(1, math.ceil(total / page_size)))


@router.post("", response_model=ActivityOut, status_code=status.HTTP_201_CREATED)
def create_activity(payload: ActivityIn, user: CurrentUser, db: DbSession, background: BackgroundTasks):
    try:
        activity = service.create_activity(db, user, **payload.model_dump())
    except CalculationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    background.add_task(refresh_user_analytics, user.id)
    return activity


@router.get("/{activity_id}", response_model=ActivityOut)
def get_activity(activity_id: uuid.UUID, user: CurrentUser, db: DbSession):
    try:
        return service.get_owned_activity(db, user, activity_id)
    except service.ActivityNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Activity not found") from exc


@router.patch("/{activity_id}", response_model=ActivityOut)
def update_activity(activity_id: uuid.UUID, payload: ActivityUpdate, user: CurrentUser, db: DbSession, background: BackgroundTasks):
    try:
        activity = service.get_owned_activity(db, user, activity_id)
    except service.ActivityNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Activity not found") from exc
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("for_organization") and user.organization_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not a member of an organization.")
    try:
        activity = service.update_activity(db, user, activity, changes)
    except CalculationError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    background.add_task(refresh_user_analytics, user.id)
    return activity


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(activity_id: uuid.UUID, user: CurrentUser, db: DbSession, background: BackgroundTasks) -> Response:
    try:
        activity = service.get_owned_activity(db, user, activity_id)
    except service.ActivityNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Activity not found") from exc
    service.delete_activity(db, activity)
    background.add_task(refresh_user_analytics, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
