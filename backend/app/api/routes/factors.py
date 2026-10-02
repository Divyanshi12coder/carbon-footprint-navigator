"""Emission factors: publicly readable (methodology transparency), writable by admins only (versioned)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select

from app.api.deps import AdminUser, DbSession, OptionalUser
from app.models import CATEGORIES, EmissionFactor
from app.schemas.common import Category
from app.schemas.factor import FactorCreate, FactorOut, FactorUpdate

router = APIRouter(prefix="/emission-factors", tags=["emission-factors"])


@router.get("/categories")
def categories() -> list[str]:
    return list(CATEGORIES)


@router.get("", response_model=list[FactorOut])
def list_factors(
    user: OptionalUser,
    db: DbSession,
    category: Category | None = None,
    region: str | None = None,
    search: Annotated[str | None, Query(max_length=80)] = None,
    include_inactive: bool = False,
) -> list[EmissionFactor]:
    stmt = select(EmissionFactor)
    if not (include_inactive and user is not None and user.role == "admin"):
        stmt = stmt.where(EmissionFactor.is_active.is_(True))
    if category:
        stmt = stmt.where(EmissionFactor.category == category)
    if region:
        stmt = stmt.where(EmissionFactor.region == region.upper())
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(EmissionFactor.name.ilike(like), EmissionFactor.key.ilike(like)))
    return list(db.scalars(stmt.order_by(EmissionFactor.category, EmissionFactor.key, EmissionFactor.region, EmissionFactor.version)))


@router.get("/{factor_id}", response_model=FactorOut)
def get_factor(factor_id: uuid.UUID, db: DbSession) -> EmissionFactor:
    factor = db.get(EmissionFactor, factor_id)
    if factor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Emission factor not found")
    return factor


@router.get("/{factor_id}/history", response_model=list[FactorOut])
def factor_history(factor_id: uuid.UUID, db: DbSession) -> list[EmissionFactor]:
    factor = get_factor(factor_id, db)
    return list(
        db.scalars(
            select(EmissionFactor)
            .where(EmissionFactor.key == factor.key, EmissionFactor.region == factor.region)
            .order_by(EmissionFactor.version.desc())
        )
    )


@router.post("", response_model=FactorOut, status_code=status.HTTP_201_CREATED)
def create_factor(payload: FactorCreate, admin: AdminUser, db: DbSession) -> EmissionFactor:
    exists = db.scalar(
        select(EmissionFactor.id).where(
            EmissionFactor.key == payload.key, EmissionFactor.region == payload.region, EmissionFactor.is_active.is_(True)
        )
    )
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "An active factor with this key and region exists; update it instead.")
    latest = db.scalar(
        select(EmissionFactor.version)
        .where(EmissionFactor.key == payload.key, EmissionFactor.region == payload.region)
        .order_by(EmissionFactor.version.desc())
    )
    factor = EmissionFactor(**payload.model_dump(), version=(latest or 0) + 1, is_active=True, updated_by_id=admin.id)
    db.add(factor)
    db.commit()
    db.refresh(factor)
    return factor


@router.put("/{factor_id}", response_model=FactorOut)
def update_factor(factor_id: uuid.UUID, payload: FactorUpdate, admin: AdminUser, db: DbSession) -> EmissionFactor:
    """Creates version N+1 and deactivates the current version. Existing records keep their factor."""
    current = db.get(EmissionFactor, factor_id)
    if current is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Emission factor not found")
    if not current.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only the active version can be updated.")
    data = {
        c: getattr(current, c)
        for c in (
            "key",
            "category",
            "name",
            "region",
            "unit",
            "co2e_per_unit",
            "source",
            "source_url",
            "year",
            "quality",
            "notes",
        )
    }
    data.update(payload.model_dump(exclude_unset=True))
    current.is_active = False
    new = EmissionFactor(**data, version=current.version + 1, is_active=True, updated_by_id=admin.id)
    db.add(new)
    db.commit()
    db.refresh(new)
    return new


@router.delete("/{factor_id}", response_model=FactorOut)
def deactivate_factor(factor_id: uuid.UUID, admin: AdminUser, db: DbSession) -> EmissionFactor:
    """Soft delete: the factor stops being used for new calculations but remains for traceability."""
    factor = db.get(EmissionFactor, factor_id)
    if factor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Emission factor not found")
    factor.is_active = False
    factor.updated_by_id = admin.id
    factor.change_reason = "Deactivated by administrator"
    db.commit()
    db.refresh(factor)
    return factor
