from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.carbon.behavior import onboarding_profile
from app.models import UserPreference, UserProfile
from app.schemas.auth import UserOut
from app.schemas.profile import (
    BaselineItemOut,
    BaselineOut,
    OnboardingIn,
    PreferencesIn,
    PreferencesOut,
    ProfileIn,
    ProfileOut,
)
from app.services import organizations
from app.services.pipeline import refresh_user_analytics

router = APIRouter(prefix="/profile", tags=["profile"])

PROFILE_FIELDS = set(ProfileIn.model_fields)


def _upsert_profile(db, user, data: dict) -> UserProfile:
    profile = user.profile or UserProfile(user_id=user.id)
    for key, value in data.items():
        if key in PROFILE_FIELDS:
            setattr(profile, key, value)
    if user.profile is None:
        db.add(profile)
        user.profile = profile
    return profile


@router.get("", response_model=ProfileOut | None)
def get_profile(user: CurrentUser) -> UserProfile | None:
    return user.profile


@router.put("", response_model=ProfileOut)
def update_profile(payload: ProfileIn, user: CurrentUser, db: DbSession, background: BackgroundTasks) -> UserProfile:
    profile = _upsert_profile(db, user, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(profile)
    background.add_task(refresh_user_analytics, user.id)
    return profile


@router.post("/onboarding", response_model=UserOut)
def complete_onboarding(payload: OnboardingIn, user: CurrentUser, db: DbSession, background: BackgroundTasks):
    data = payload.model_dump(exclude_unset=True)
    _upsert_profile(db, user, data)
    user.onboarding_completed = True
    db.commit()
    if payload.organization_name and not user.organization_id:
        try:
            organizations.create(
                db,
                user,
                payload.organization_name,
                payload.organization_industry,
                payload.country,
                payload.organization_employee_count,
            )
        except organizations.OrganizationError as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    db.refresh(user)
    background.add_task(refresh_user_analytics, user.id)
    return user


@router.get("/baseline", response_model=BaselineOut)
def baseline(user: CurrentUser, db: DbSession) -> BaselineOut:
    """Estimated footprint from onboarding answers (used before enough activities are tracked)."""
    est = onboarding_profile(db, user.profile)
    return BaselineOut(
        basis=est.basis,
        monthly_total_kg=round(est.monthly_total_kg, 2),
        annual_total_kg=round(est.monthly_total_kg * 12, 1),
        by_category_monthly_kg={k: round(v, 2) for k, v in est.by_category().items()},
        items=[
            BaselineItemOut(
                factor_key=i.factor_key,
                category=i.category,
                monthly_quantity=round(i.monthly_quantity, 3),
                unit=i.unit,
                factor_value=i.factor_value,
                monthly_kg=round(i.monthly_kg, 3),
            )
            for i in est.items
        ],
        assumptions=est.assumptions,
    )


@router.get("/preferences", response_model=PreferencesOut)
def get_preferences(user: CurrentUser, db: DbSession) -> UserPreference:
    if user.preferences is None:
        user.preferences = UserPreference()
        db.commit()
    return user.preferences


@router.put("/preferences", response_model=PreferencesOut)
def update_preferences(payload: PreferencesIn, user: CurrentUser, db: DbSession) -> UserPreference:
    prefs = user.preferences or UserPreference()
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None or key == "monthly_budget_kg":
            setattr(prefs, key, value)
    user.preferences = prefs
    db.commit()
    db.refresh(prefs)
    return prefs
