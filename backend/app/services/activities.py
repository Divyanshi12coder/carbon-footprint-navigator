"""Activity lifecycle: validate -> calculate -> store activity + emission record."""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.carbon.engine import CalculationResult, calculate
from app.models import Activity, EmissionRecord, User

SORT_COLUMNS = {
    "occurred_on": Activity.occurred_on,
    "created_at": Activity.created_at,
    "co2e_kg": EmissionRecord.co2e_kg,
    "category": Activity.category,
}


class ActivityNotFound(LookupError):
    pass


def user_region(user: User) -> str | None:
    return user.profile.country if user.profile else None


def _apply_result(activity: Activity, record: EmissionRecord, result: CalculationResult) -> None:
    activity.category = result.category
    activity.activity_type = result.activity_type
    activity.quantity = result.quantity
    activity.unit = result.unit
    activity.details = result.details
    record.user_id = activity.user_id
    record.organization_id = activity.organization_id
    record.category = result.category
    record.activity_type = result.activity_type
    record.occurred_on = activity.occurred_on
    record.emission_factor_id = result.factor.id if result.factor else None
    record.factor_key = result.factor_key
    record.factor_value = result.factor_value
    record.factor_unit = result.factor_unit
    record.factor_source = result.factor_source
    record.normalized_quantity = result.normalized_quantity
    record.co2e_kg = result.co2e_kg
    record.calculation_method = result.calculation_method
    record.data_quality = result.data_quality
    record.assumptions = result.assumptions


def create_activity(db: Session, user: User, **kwargs: Any) -> Activity:
    activity = build_activity(db, user, **kwargs)
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


def build_activity(
    db: Session,
    user: User,
    *,
    activity_type: str,
    quantity: float | None,
    unit: str | None,
    occurred_on: date,
    details: dict[str, Any],
    description: str | None,
    for_organization: bool = False,
    source: str = "manual",
) -> Activity:
    """Calculate and build (but do not commit) an activity with its emission record."""
    if for_organization and user.organization_id is None:
        raise PermissionError("You are not a member of an organization.")
    result = calculate(db, activity_type, quantity, unit, details, user_region(user))
    activity = Activity(
        user_id=user.id,
        organization_id=user.organization_id if for_organization else None,
        occurred_on=occurred_on,
        description=description,
        source=source,
        category=result.category,
        activity_type=result.activity_type,
        quantity=result.quantity,
        unit=result.unit,
        details=result.details,
    )
    record = EmissionRecord()
    activity.emission = record
    _apply_result(activity, record, result)
    return activity


def get_owned_activity(db: Session, user: User, activity_id: uuid.UUID) -> Activity:
    activity = db.get(Activity, activity_id)
    # 404 (not 403) for other users' activities so IDs cannot be probed.
    if activity is None or activity.user_id != user.id:
        raise ActivityNotFound()
    return activity


def update_activity(db: Session, user: User, activity: Activity, changes: dict[str, Any]) -> Activity:
    activity_type = changes.get("activity_type", activity.activity_type)
    details = changes.get("details", activity.details)
    quantity = changes.get("quantity", activity.quantity)
    unit = changes.get("unit", activity.unit)
    # Flights store the derived distance; recompute from airports when they are given.
    if activity_type == "flight" and details.get("origin") and "quantity" not in changes:
        quantity = None
    result = calculate(db, activity_type, quantity, unit, details, user_region(user))
    if "occurred_on" in changes:
        activity.occurred_on = changes["occurred_on"]
    if "description" in changes:
        activity.description = changes["description"]
    if "for_organization" in changes:
        activity.organization_id = user.organization_id if changes["for_organization"] else None
    _apply_result(activity, activity.emission, result)
    db.commit()
    db.refresh(activity)
    return activity


def delete_activity(db: Session, activity: Activity) -> None:
    db.delete(activity)
    db.commit()


def list_activities(
    db: Session,
    user: User,
    *,
    page: int,
    page_size: int,
    category: str | None = None,
    activity_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    scope: str = "personal",
    sort: str = "occurred_on",
    order: str = "desc",
) -> tuple[list[Activity], int]:
    stmt: Select = select(Activity).join(EmissionRecord, EmissionRecord.activity_id == Activity.id)
    if scope == "organization":
        stmt = stmt.where(Activity.user_id == user.id, Activity.organization_id.is_not(None))
    elif scope == "all":
        stmt = stmt.where(Activity.user_id == user.id)
    else:
        stmt = stmt.where(Activity.user_id == user.id, Activity.organization_id.is_(None))
    if category:
        stmt = stmt.where(Activity.category == category)
    if activity_type:
        stmt = stmt.where(Activity.activity_type == activity_type)
    if date_from:
        stmt = stmt.where(Activity.occurred_on >= date_from)
    if date_to:
        stmt = stmt.where(Activity.occurred_on <= date_to)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(or_(Activity.description.ilike(like), Activity.activity_type.ilike(like)))

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    column = SORT_COLUMNS.get(sort, Activity.occurred_on)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), Activity.created_at.desc())
    items = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).unique().all()
    return list(items), int(total)
