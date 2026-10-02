"""Test fixtures.

Tests run against a real PostgreSQL database (TEST_DATABASE_URL), migrated with Alembic, so
queries, constraints and migrations are exercised exactly as in production.
"""

import os
import uuid
from collections.abc import Iterator
from datetime import date, timedelta

import pytest

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://cfn:cfn_dev_password@localhost:5433/cfn_test")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = "test-secret-that-is-long-enough-for-hs256-signing"
os.environ["AI_PROVIDER"] = "demo"
os.environ["AI_API_KEY"] = ""
os.environ["RATE_LIMIT_AUTH_PER_MINUTE"] = "1000"
os.environ["RATE_LIMIT_ASSISTANT_PER_MINUTE"] = "1000"

from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from alembic import command  # noqa: E402
from app.carbon.factors import seed_emission_factors  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_TABLES = [
    "messages",
    "conversations",
    "insights",
    "predictions",
    "recommendations",
    "goals",
    "achievements",
    "emission_records",
    "activities",
    "user_preferences",
    "user_profiles",
    "users",
    "organizations",
]


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Iterator[None]:
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    command.upgrade(cfg, "head")
    with SessionLocal() as db:
        seed_emission_factors(db)
    yield


@pytest.fixture(autouse=True)
def clean_tables() -> Iterator[None]:
    yield
    with engine.begin() as conn:
        # Restore factors an admin test may have versioned/deactivated (before users go: FK to records).
        conn.execute(text("DELETE FROM emission_records"))
        conn.execute(text("DELETE FROM emission_factors WHERE version > 1"))
        conn.execute(text("UPDATE emission_factors SET is_active = true, updated_by_id = NULL"))
        # DELETE (not TRUNCATE ... CASCADE, which would also wipe emission_factors via updated_by_id).
        for table in USER_TABLES:
            conn.execute(text(f"DELETE FROM {table}"))
    limiter.reset()


@pytest.fixture
def db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def register(client: TestClient, email: str | None = None, password: str = "Sup3rSecret!", name: str = "Test User") -> dict:
    email = email or f"user-{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post("/api/auth/register", json={"email": email, "password": password, "full_name": name})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return {
        "email": email,
        "password": password,
        "token": body["access_token"],
        "user": body["user"],
        "headers": {"Authorization": f"Bearer {body['access_token']}"},
    }


@pytest.fixture
def user(client: TestClient) -> dict:
    return register(client)


@pytest.fixture
def other_user(client: TestClient) -> dict:
    return register(client, name="Other User")


def add_activity(
    client: TestClient, headers: dict, activity_type: str, quantity: float | None, unit: str | None, days_ago: int = 0, **details
) -> dict:
    resp = client.post(
        "/api/activities",
        headers=headers,
        json={
            "activity_type": activity_type,
            "quantity": quantity,
            "unit": unit,
            "occurred_on": (date.today() - timedelta(days=days_ago)).isoformat(),
            "details": details,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def get_user(db: Session, user_id: str) -> User:
    return db.get(User, uuid.UUID(user_id))
