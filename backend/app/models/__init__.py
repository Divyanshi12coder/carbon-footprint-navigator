"""Import every model so Base.metadata is complete (used by Alembic and tests)."""

from app.models.carbon import CATEGORIES, Activity, EmissionFactor, EmissionRecord
from app.models.engagement import Conversation, Goal, Insight, Message, Prediction, Recommendation
from app.models.user import Achievement, Organization, User, UserPreference, UserProfile

__all__ = [
    "CATEGORIES",
    "Achievement",
    "Activity",
    "Conversation",
    "EmissionFactor",
    "EmissionRecord",
    "Goal",
    "Insight",
    "Message",
    "Organization",
    "Prediction",
    "Recommendation",
    "User",
    "UserPreference",
    "UserProfile",
]
