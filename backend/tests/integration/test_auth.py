"""Full auth flow against a real database — register, login, protected
endpoint, refresh rotation, logout. Same opt-in gating as
test_models_db.py: `RUN_INTEGRATION_TESTS=1` + a real `DATABASE_URL`.

This exact flow was driven manually via curl during Phase 5 development and
caught two real bugs, now fixed and covered here:
  1. passlib's bcrypt self-test crashes against bcrypt>=4.1's stricter
     >72-byte handling — switched to using `bcrypt` directly (app/core/security.py).
  2. The global RFC 7807 exception handler dropped `HTTPException.headers`,
     silently discarding `WWW-Authenticate: Bearer` on 401s
     (app/middlewares/error_handlers.py).
"""

import os
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS") != "1",
    reason="opt-in: set RUN_INTEGRATION_TESTS=1 and DATABASE_URL to a disposable pg+pgvector db",
)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def _unique_email() -> str:
    return f"{uuid.uuid4().hex}@example.com"


def test_full_auth_flow(client: TestClient) -> None:
    email = _unique_email()
    password = "correct-horse-battery-staple"

    # 1. Register
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Ada Lovelace"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["email"] == email

    # 2. Duplicate registration is rejected
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Ada Lovelace"},
    )
    assert resp.status_code == 409

    # 3. Login with the wrong password fails
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "wrong"})
    assert resp.status_code == 401

    # 4. Login with the right password succeeds
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    tokens = resp.json()
    access_token, refresh_token = tokens["access_token"], tokens["refresh_token"]

    # 5. Protected endpoint rejects missing/invalid credentials, with WWW-Authenticate
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"

    # 6. Protected endpoint accepts a valid access token
    resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == email

    # 7. Refresh rotates the token — the old refresh token is no longer valid
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    new_refresh_token = resp.json()["refresh_token"]
    assert new_refresh_token != refresh_token

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401

    # 8. Logout revokes the current refresh token
    resp = client.post("/api/v1/auth/logout", json={"refresh_token": new_refresh_token})
    assert resp.status_code == 204

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh_token})
    assert resp.status_code == 401


def test_register_rejects_short_password(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": _unique_email(), "password": "short", "full_name": "X"},
    )
    assert resp.status_code == 422


def test_oauth_login_rejects_unconfigured_provider(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/oauth/google", follow_redirects=False)
    assert resp.status_code == 404
