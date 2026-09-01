"""Unit tests for app.core.security — pure crypto/encoding with no DB or
FastAPI dependency (see that module's docstring), so these run instantly with
no live infra, unlike test_auth.py's integration coverage of the same logic
wired through the real HTTP endpoints."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.core.config import Settings
from app.core.exceptions import InvalidTokenError
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


@pytest.fixture
def settings() -> Settings:
    return Settings(secret_key="test-secret-key", access_token_expire_minutes=15)


def test_hash_password_never_returns_the_plaintext() -> None:
    hashed = hash_password("correct-horse-battery-staple")
    assert hashed != "correct-horse-battery-staple"


def test_hash_password_is_salted_so_the_same_password_hashes_differently() -> None:
    assert hash_password("same-password") != hash_password("same-password")


def test_verify_password_accepts_the_correct_password_and_rejects_others() -> None:
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("correct-horse-battery-staple", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_verify_password_truncates_beyond_72_bytes_consistently() -> None:
    # bcrypt's own hard limit (see the module docstring) — hash_password and
    # verify_password must truncate identically, or a password that happens
    # to differ only after byte 72 would wrongly fail to verify.
    long_password = "a" * 100
    hashed = hash_password(long_password)
    assert verify_password("a" * 100, hashed) is True
    assert verify_password("a" * 72 + "b" * 28, hashed) is True


def test_access_token_round_trips_the_user_id(settings: Settings) -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id, settings)
    assert decode_access_token(token, settings) == user_id


def test_decode_access_token_rejects_a_malformed_token(settings: Settings) -> None:
    with pytest.raises(InvalidTokenError):
        decode_access_token("not-a-real-jwt", settings)


def test_decode_access_token_rejects_a_token_signed_with_a_different_key(
    settings: Settings,
) -> None:
    token = create_access_token(uuid.uuid4(), settings)
    other_settings = Settings(secret_key="a-completely-different-key")
    with pytest.raises(InvalidTokenError):
        decode_access_token(token, other_settings)


def test_decode_access_token_rejects_an_expired_token(settings: Settings) -> None:
    now = datetime.now(UTC)
    payload = {
        "sub": str(uuid.uuid4()),
        "type": "access",
        "iat": now - timedelta(minutes=30),
        "exp": now - timedelta(minutes=15),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(InvalidTokenError):
        decode_access_token(token, settings)


def test_decode_access_token_rejects_a_token_with_the_wrong_type_claim(
    settings: Settings,
) -> None:
    # A hand-crafted token that's otherwise validly signed but isn't one
    # create_access_token ever issues (e.g. a refresh-token-shaped JWT, or a
    # token forged for a different purpose) must not be accepted here.
    payload = {"sub": str(uuid.uuid4()), "type": "refresh"}
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(InvalidTokenError):
        decode_access_token(token, settings)


def test_decode_access_token_rejects_a_missing_or_invalid_subject(settings: Settings) -> None:
    payload = {"type": "access", "sub": "not-a-uuid"}
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(InvalidTokenError):
        decode_access_token(token, settings)


def test_generate_refresh_token_returns_a_high_entropy_raw_token_and_its_hash() -> None:
    raw_token, token_hash = generate_refresh_token()
    assert raw_token != token_hash
    assert len(raw_token) >= 32
    other_raw_token, _ = generate_refresh_token()
    assert raw_token != other_raw_token


def test_hash_refresh_token_is_deterministic_and_matches_generate_refresh_token() -> None:
    raw_token, token_hash = generate_refresh_token()
    assert hash_refresh_token(raw_token) == token_hash
    assert hash_refresh_token(raw_token) == hash_refresh_token(raw_token)
