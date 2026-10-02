"""Post-write analytics pipeline.

Runs after activities change (as a FastAPI background task, with its own DB session):
recompute recommendations, regenerate insights, award achievements.
"""

import logging
import uuid

from app.db.session import SessionLocal
from app.models import User
from app.services import achievements, insights, ml_service

logger = logging.getLogger(__name__)


def refresh_user_analytics(user_id: uuid.UUID) -> None:
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if user is None:
            return
        ml_service.refresh_recommendations(db, user)
        insights.refresh_insights(db, user)
        achievements.check_and_award(db, user)
    except Exception:  # never let a background refresh crash the worker
        logger.exception("Analytics refresh failed for user %s", user_id)
        db.rollback()
    finally:
        db.close()
