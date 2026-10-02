"""Organization mode: shared company footprint built from members' business activities."""

import secrets
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import EmissionRecord, Organization, User

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no ambiguous 0/O/1/I


class OrganizationError(ValueError):
    pass


def _join_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(10))


def create(db: Session, user: User, name: str, industry: str | None, country: str | None, employee_count: int | None) -> Organization:
    if user.organization_id:
        raise OrganizationError("Leave your current organization before creating a new one.")
    org = Organization(
        name=name.strip(),
        industry=industry,
        country=country,
        employee_count=employee_count,
        join_code=_join_code(),
        created_by_id=user.id,
    )
    db.add(org)
    db.flush()
    user.organization_id, user.org_role = org.id, "owner"
    db.commit()
    db.refresh(org)
    return org


def join(db: Session, user: User, code: str) -> Organization:
    if user.organization_id:
        raise OrganizationError("You already belong to an organization.")
    org = db.scalar(select(Organization).where(Organization.join_code == code.strip().upper()))
    if org is None:
        raise OrganizationError("Invalid join code.")
    user.organization_id, user.org_role = org.id, "member"
    db.commit()
    return org


def leave(db: Session, user: User) -> None:
    if not user.organization_id:
        raise OrganizationError("You are not in an organization.")
    if user.org_role == "owner":
        others = db.scalar(select(func.count(User.id)).where(User.organization_id == user.organization_id, User.id != user.id))
        if others:
            raise OrganizationError("Owners cannot leave while other members remain.")
    user.organization_id, user.org_role = None, None
    db.commit()


def members(db: Session, org: Organization) -> list[dict[str, Any]]:
    rows = db.execute(
        select(
            User.id,
            User.full_name,
            User.org_role,
            func.coalesce(func.sum(EmissionRecord.co2e_kg), 0.0),
            func.count(EmissionRecord.id),
        )
        .outerjoin(EmissionRecord, (EmissionRecord.user_id == User.id) & (EmissionRecord.organization_id == org.id))
        .where(User.organization_id == org.id)
        .group_by(User.id, User.full_name, User.org_role)
        .order_by(User.full_name)
    ).all()
    return [
        {
            "user_id": str(uid),
            "full_name": name,
            "org_role": role,
            "contributed_kg": round(float(kg), 2),
            "activity_count": int(n),
        }
        for uid, name, role, kg, n in rows
    ]
