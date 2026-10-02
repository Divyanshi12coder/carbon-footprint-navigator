"""Optional demo data: a realistic ~6 month history for one demo user.

Every demo activity goes through the same calculation engine as user input — the seed only
decides *what* the demo person did, never the CO2e values.
"""

import logging
import random
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Goal, User, UserPreference, UserProfile
from app.services import achievements, insights, ml_service
from app.services import goals as goal_service
from app.services.activities import build_activity

logger = logging.getLogger(__name__)
DAYS = 182

MEALS = [
    ("chicken", 0.28),
    ("beef", 0.12),
    ("pork", 0.08),
    ("fish", 0.10),
    ("vegetarian", 0.25),
    ("vegan", 0.10),
    ("dairy_heavy", 0.07),
]


def _meal(rng: random.Random) -> str:
    r, acc = rng.random(), 0.0
    for meal, p in MEALS:
        acc += p
        if r <= acc:
            return meal
    return MEALS[-1][0]


def _demo_plan(today: date, rng: random.Random) -> list[dict]:
    start = today - timedelta(days=DAYS - 1)
    acts: list[dict] = []

    def add(day: date, activity_type: str, quantity: float | None, unit: str | None, details: dict, description: str) -> None:
        acts.append(
            dict(
                activity_type=activity_type,
                quantity=quantity,
                unit=unit,
                occurred_on=day,
                details=details,
                description=description,
                source="seed",
            )
        )

    for i in range(DAYS):
        day = start + timedelta(days=i)
        recent = (today - day).days < 7
        winter = day.month in (11, 12, 1, 2, 3)
        if day.weekday() < 5:
            if rng.random() < 0.7:
                add(
                    day,
                    "car",
                    round(rng.uniform(16, 21), 1) * 2,
                    "km",
                    {"fuel_type": "petrol", "occupants": 1},
                    "Commute (return)",
                )
            else:
                add(day, "public_transport", round(rng.uniform(20, 24), 1) * 2, "km", {"mode": "rail"}, "Train commute (return)")
        else:
            if rng.random() < 0.55:
                add(day, "car", round(rng.uniform(15, 60), 1), "km", {"fuel_type": "petrol", "occupants": 2}, "Weekend trip")
            if rng.random() < 0.5:
                add(day, "active_travel", round(rng.uniform(5, 15), 1), "km", {"mode": "bicycle"}, "Bike ride")
        if recent and day.weekday() >= 4:
            add(
                day,
                "car",
                round(rng.uniform(140, 190), 1),
                "km",
                {"fuel_type": "petrol", "occupants": 1},
                "Road trip to visit family",
            )

        for _ in range(2):
            add(day, "meal", 1, "serving", {"meal_type": _meal(rng)}, "Lunch / dinner")
        if rng.random() < 0.6:
            add(day, "streaming", round(rng.uniform(0.5, 2.5), 1), "hour", {}, "Evening streaming")

        if day.weekday() == 6:
            add(
                day,
                "electricity",
                round(rng.uniform(55, 70) * (1.2 if winter else 1.0), 1),
                "kWh",
                {"source": "grid"},
                "Weekly meter reading",
            )
            add(
                day,
                "natural_gas",
                round(rng.uniform(150, 210) if winter else rng.uniform(40, 70), 1),
                "kWh",
                {},
                "Weekly gas reading",
            )
            add(day, "waste", round(rng.uniform(5, 7.5), 1), "kg", {"method": "landfill"}, "General waste bin")
            add(day, "waste", round(rng.uniform(3, 4.5), 1), "kg", {"method": "recycling"}, "Recycling bin")
        if day.day == 15:
            add(day, "purchase", round(rng.uniform(50, 130), 0), "USD", {"item_category": "clothing"}, "Clothes shopping")

    def on(days_ago: int) -> date:
        return today - timedelta(days=days_ago)

    add(
        on(150),
        "flight",
        None,
        None,
        {"origin": "EDI", "destination": "LHR", "cabin_class": "economy", "passengers": 1, "round_trip": True},
        "Work trip to London",
    )
    add(
        on(118),
        "flight",
        None,
        None,
        {"origin": "LHR", "destination": "BCN", "cabin_class": "economy", "passengers": 2, "round_trip": True},
        "Holiday in Barcelona",
    )
    add(
        on(64),
        "flight",
        None,
        None,
        {"origin": "LHR", "destination": "JFK", "cabin_class": "economy", "passengers": 1, "round_trip": True},
        "Conference in New York",
    )
    add(on(62), "hotel_stay", 3, "room_night", {}, "Conference hotel")
    add(on(95), "product", 1, "item", {"product": "laptop"}, "New work laptop")
    return acts


def seed_demo_user(db: Session, email: str, password: str, today: date | None = None) -> User | None:
    today = today or date.today()
    if db.scalar(select(User).where(User.email == email)):
        logger.info("Demo user already exists; skipping demo seed.")
        return None
    user = User(email=email, hashed_password=hash_password(password), full_name="Alex Rivera", onboarding_completed=True)
    user.profile = UserProfile(
        country="GB",
        region="Greater Manchester",
        household_size=2,
        primary_transport="car",
        vehicle_type="petrol",
        weekly_car_km=180,
        weekly_public_transport_km=50,
        short_haul_flights_per_year=2,
        long_haul_flights_per_year=1,
        monthly_electricity_kwh=520,
        renewable_share_pct=0,
        heating_fuel="natural_gas",
        monthly_heating_kwh=900,
        diet_type="mixed",
        shopping_level="medium",
        weekly_waste_kg=12,
        recycling_level="some",
        composts=False,
    )
    user.preferences = UserPreference(distance_unit="km", default_range="90d")
    db.add(user)
    db.flush()

    rng = random.Random(42)
    for spec in _demo_plan(today, rng):
        db.add(build_activity(db, user, **spec))
    db.flush()
    # Goal baselines come from the demo user's own emissions in the 30 days before each goal started.
    for title, category, pct, started_ago, deadline_in in (
        ("Cut monthly emissions by 15%", None, 15, 10, 110),
        ("Cut transport emissions by 20%", "transport", 20, 45, 75),
        ("Halve food emissions", "food", 50, 20, 160),
    ):
        start_date = today - timedelta(days=started_ago)
        baseline = goal_service.monthly_emissions(db, user.id, category, start_date - timedelta(days=30), start_date - timedelta(days=1))
        db.add(
            Goal(
                user_id=user.id,
                title=title,
                category=category,
                baseline_monthly_kg=round(baseline * goal_service.DAYS_PER_MONTH / 30, 2),
                target_reduction_pct=pct,
                start_date=start_date,
                deadline=today + timedelta(days=deadline_in),
            )
        )
    db.commit()

    ml_service.refresh_recommendations(db, user, today)
    insights.refresh_insights(db, user, today)
    achievements.check_and_award(db, user)
    logger.info("Seeded demo user %s", email)
    return user
