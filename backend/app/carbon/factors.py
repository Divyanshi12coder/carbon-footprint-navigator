"""Emission-factor repository: lookup with regional fallback, seeding and versioned updates."""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EmissionFactor

GLOBAL = "GLOBAL"
DATA_FILE = Path(__file__).parent / "data" / "emission_factors.json"


class FactorNotFoundError(LookupError):
    pass


def get_active_factor(db: Session, key: str, region: str | None = None) -> tuple[EmissionFactor, bool]:
    """Return (factor, used_fallback). Tries the requested region first, then GLOBAL."""
    regions = [r for r in ((region or "").upper(), GLOBAL) if r]
    rows = db.scalars(
        select(EmissionFactor).where(
            EmissionFactor.key == key,
            EmissionFactor.is_active.is_(True),
            EmissionFactor.region.in_(regions),
        )
    ).all()
    by_region = {r.region: r for r in rows}
    for idx, r in enumerate(regions):
        if r in by_region:
            used_fallback = idx > 0 and bool(region) and region.upper() != GLOBAL
            return by_region[r], used_fallback
    raise FactorNotFoundError(f"No active emission factor for '{key}' (region {region or GLOBAL}).")


def load_seed_factors() -> list[dict]:
    with DATA_FILE.open(encoding="utf-8") as fh:
        return json.load(fh)


def seed_emission_factors(db: Session) -> int:
    """Insert factors from the bundled dataset that are missing. Idempotent; never overwrites edits."""
    existing = {(k, r) for k, r in db.execute(select(EmissionFactor.key, EmissionFactor.region)).all()}
    created = 0
    for row in load_seed_factors():
        if (row["key"], row["region"]) in existing:
            continue
        db.add(EmissionFactor(**row, version=1, is_active=True, change_reason="Initial dataset import"))
        created += 1
    db.commit()
    return created
