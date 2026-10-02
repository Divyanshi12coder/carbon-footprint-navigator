from fastapi import APIRouter

from app.api.routes import activities, assistant, auth, emissions, factors, goals, intelligence, misc, organizations, profile

api_router = APIRouter(prefix="/api")
for router in (
    misc.health_router,
    auth.router,
    profile.router,
    activities.router,
    emissions.dashboard_router,
    emissions.emissions_router,
    factors.router,
    intelligence.insights_router,
    intelligence.recommendations_router,
    intelligence.forecast_router,
    intelligence.anomalies_router,
    intelligence.scenarios_router,
    goals.router,
    assistant.router,
    organizations.router,
    misc.achievements_router,
):
    api_router.include_router(router)
