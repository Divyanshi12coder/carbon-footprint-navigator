from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import select, text

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.models import Achievement
from app.schemas.engagement import AchievementOut
from app.services import achievements

health_router = APIRouter(tags=["health"])
achievements_router = APIRouter(prefix="/achievements", tags=["achievements"])


@health_router.get("/health")
def health(db: DbSession) -> Any:
    settings = get_settings()
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:  # noqa: BLE001 — report, don't crash the probe
        database = "unavailable"
    body = {
        "status": "ok" if database == "ok" else "degraded",
        "database": database,
        "environment": settings.environment,
        "ai_mode": "llm" if settings.ai_enabled else "demo",
    }
    return JSONResponse(body, status_code=status.HTTP_200_OK if database == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE)


@achievements_router.get("", response_model=list[AchievementOut])
def list_achievements(user: CurrentUser, db: DbSession) -> list[AchievementOut]:
    achievements.check_and_award(db, user)
    earned = {a.code: a for a in db.scalars(select(Achievement).where(Achievement.user_id == user.id))}
    return [
        AchievementOut(
            **item,
            achieved=item["code"] in earned,
            achieved_at=earned[item["code"]].achieved_at if item["code"] in earned else None,
        )
        for item in achievements.catalogue()
    ]
