from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import get_settings
from tests.conftest import register


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["database"] == "ok"


def test_register_login_me(client):
    reg = register(client, email="Alice@Example.com")
    assert reg["user"]["email"] == "alice@example.com"
    assert reg["user"]["onboarding_completed"] is False

    resp = client.post("/api/auth/login", json={"email": "alice@example.com", "password": reg["password"]})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"


def test_password_is_hashed(client, db):
    reg = register(client)
    from tests.conftest import get_user

    stored = get_user(db, reg["user"]["id"]).hashed_password
    assert stored != reg["password"]
    assert stored.startswith("$2b$")


def test_duplicate_email_rejected(client):
    register(client, email="dup@example.com")
    resp = client.post("/api/auth/register", json={"email": "DUP@example.com", "password": "Another1pass", "full_name": "X"})
    assert resp.status_code == 409


def test_weak_password_rejected(client):
    resp = client.post("/api/auth/register", json={"email": "weak@example.com", "password": "password", "full_name": "W"})
    assert resp.status_code == 422


def test_wrong_password_and_unknown_email(client):
    register(client, email="bob@example.com")
    assert client.post("/api/auth/login", json={"email": "bob@example.com", "password": "wrong-pass1"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "wrong-pass1"}).status_code == 401


def test_protected_routes_require_token(client):
    for path in ("/api/auth/me", "/api/activities", "/api/dashboard/summary", "/api/goals", "/api/forecast"):
        assert client.get(path).status_code == 401, path


def test_invalid_and_expired_tokens(client, user):
    bad = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert bad.status_code == 401

    settings = get_settings()
    expired = jwt.encode(
        {
            "sub": user["user"]["id"],
            "tv": 0,
            "type": "access",
            "iat": datetime.now(UTC) - timedelta(hours=2),
            "exp": datetime.now(UTC) - timedelta(hours=1),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()

    forged = jwt.encode(
        {"sub": user["user"]["id"], "tv": 0, "type": "access", "iat": datetime.now(UTC), "exp": datetime.now(UTC) + timedelta(hours=1)},
        "a-different-secret-of-sufficient-length!!",
        algorithm="HS256",
    )
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_logout_revokes_token(client, user):
    assert client.get("/api/auth/me", headers=user["headers"]).status_code == 200
    assert client.post("/api/auth/logout", headers=user["headers"]).status_code == 200
    assert client.get("/api/auth/me", headers=user["headers"]).status_code == 401


def test_change_password(client, user):
    resp = client.post(
        "/api/auth/change-password", headers=user["headers"], json={"current_password": user["password"], "new_password": "N3wPassword!"}
    )
    assert resp.status_code == 200
    # Old token revoked, new password works.
    assert client.get("/api/auth/me", headers=user["headers"]).status_code == 401
    assert client.post("/api/auth/login", json={"email": user["email"], "password": "N3wPassword!"}).status_code == 200


def test_login_rate_limited(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_auth_per_minute", 3)
    for _ in range(3):
        client.post("/api/auth/login", json={"email": "x@example.com", "password": "whatever1"})
    resp = client.post("/api/auth/login", json={"email": "x@example.com", "password": "whatever1"})
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers
