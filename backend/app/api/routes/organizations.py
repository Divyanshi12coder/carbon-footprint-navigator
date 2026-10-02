from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.models import Organization
from app.schemas.common import MessageOut, RangeKey
from app.schemas.engagement import JoinOrganizationIn, OrganizationIn, OrganizationOut
from app.services import analytics, organizations
from app.services.analytics import Scope

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _require_org(db, user) -> Organization:
    if user.organization_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "You are not a member of an organization.")
    return db.get(Organization, user.organization_id)


def _out(org: Organization, user) -> OrganizationOut:
    out = OrganizationOut.model_validate(org)
    # Only owners see the join code.
    out.join_code = org.join_code if user.org_role == "owner" else None
    return out


@router.post("", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
def create_organization(payload: OrganizationIn, user: CurrentUser, db: DbSession) -> OrganizationOut:
    try:
        org = organizations.create(
            db, user, payload.name, payload.industry, payload.country.upper() if payload.country else None, payload.employee_count
        )
    except organizations.OrganizationError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return _out(org, user)


@router.post("/join", response_model=OrganizationOut)
def join_organization(payload: JoinOrganizationIn, user: CurrentUser, db: DbSession) -> OrganizationOut:
    try:
        org = organizations.join(db, user, payload.join_code)
    except organizations.OrganizationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return _out(org, user)


@router.post("/leave", response_model=MessageOut)
def leave_organization(user: CurrentUser, db: DbSession) -> MessageOut:
    try:
        organizations.leave(db, user)
    except organizations.OrganizationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return MessageOut(detail="You have left the organization.")


@router.get("/me", response_model=OrganizationOut)
def my_organization(user: CurrentUser, db: DbSession) -> OrganizationOut:
    return _out(_require_org(db, user), user)


@router.get("/me/members")
def members(user: CurrentUser, db: DbSession) -> list[dict[str, Any]]:
    return organizations.members(db, _require_org(db, user))


@router.get("/me/dashboard")
def org_dashboard(
    user: CurrentUser, db: DbSession, range: RangeKey = "90d", start: date | None = None, end: date | None = None
) -> dict[str, Any]:
    """Company footprint from all members' activities logged for the organization."""
    org = _require_org(db, user)
    try:
        s, e = analytics.resolve_range(range, start, end)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    scope = Scope(organization_id=org.id)
    return {
        **analytics.dashboard_summary(db, scope, s, e),
        "by_activity": analytics.by_activity(db, scope, s, e),
        "monthly": analytics.monthly_comparison(db, scope, 12),
    }
