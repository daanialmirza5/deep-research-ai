"""Password hashing, access-token (JWT) issuance/verification, and refresh-
token generation/hashing. No DB or FastAPI imports here — this module is
pure crypto/encoding, callable from services and tests alike.

Refresh tokens are deliberately NOT JWTs: they're high-entropy opaque
strings, hashed (SHA-256) before being persisted (see
app.models.auth.RefreshToken.token_hash), so a stolen database dump doesn't
hand out valid refresh tokens the way a stolen JWT signing key would.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.core.config import Settings
from app.core.exceptions import InvalidTokenError

_ACCESS_TOKEN_TYPE = "access"

# bcrypt's own hard limit; enforced at the schema layer too (UserCreate.password
# max_length=72) so an over-long password is a clean 422, not a crash here.
_MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    # Used directly rather than through passlib's CryptContext: passlib
    # (largely unmaintained) does its own bcrypt self-test with a fixed
    # vector, which raises ValueError against bcrypt>=4.1's stricter
    # >72-byte rejection — a real crash hit during Phase 5 live verification,
    # unrelated to the actual password being hashed.
    encoded = password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    encoded = plain_password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    return bcrypt.checkpw(encoded, hashed_password.encode("utf-8"))


def create_access_token(user_id: uuid.UUID, settings: Settings) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": _ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> uuid.UUID:
    """Returns the authenticated user's id, or raises InvalidTokenError."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise InvalidTokenError("Token is malformed, expired, or has an invalid signature") from exc

    if payload.get("type") != _ACCESS_TOKEN_TYPE:
        raise InvalidTokenError("Token is not an access token")

    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise InvalidTokenError("Token subject is missing or not a valid user id") from exc


def generate_refresh_token() -> tuple[str, str]:
    """Returns (raw_token, token_hash). Only the hash is ever persisted; the
    raw token is returned to the client once, at issuance."""
    raw_token = secrets.token_urlsafe(32)
    return raw_token, hash_refresh_token(raw_token)


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
