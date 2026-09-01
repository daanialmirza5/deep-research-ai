"""Registration, login, token refresh/rotation, logout, and OAuth
account resolution. Raises app.services.exceptions on failure — routers
translate those to HTTP responses (see app/api/v1/auth.py).
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.auth import RefreshToken
from app.models.user import User
from app.repositories.analytics_event import AnalyticsEventRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import TokenPair
from app.services.exceptions import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
        self.analytics_events = AnalyticsEventRepository(session)

    async def register(self, email: str, password: str, full_name: str) -> User:
        if await self.users.get_by_email(email) is not None:
            raise EmailAlreadyRegisteredError(email)
        # UUIDPrimaryKeyMixin's `default=uuid.uuid4` is a column default —
        # SQLAlchemy only calls it at flush time, so a freshly constructed
        # User's `.id` is still None here (caught live: an earlier version
        # referenced `user.id` at this point and every emitted
        # "user.registered" event silently got user_id=NULL). Generating it
        # ourselves makes it available immediately for the analytics event
        # below, in the same transaction as the INSERT it describes.
        user_id = uuid.uuid4()
        user = User(
            id=user_id, email=email, hashed_password=hash_password(password), full_name=full_name
        )
        self.analytics_events.record("user.registered", user_id=user_id)
        return await self.users.create(user)

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.users.get_by_email(email)
        if user is None or user.hashed_password is None:
            raise InvalidCredentialsError
        if not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError
        if not user.is_active:
            raise InactiveUserError
        return user

    async def issue_token_pair(self, user: User) -> TokenPair:
        access_token = create_access_token(user.id, self.settings)
        raw_refresh_token, token_hash = generate_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(days=self.settings.refresh_token_expire_days)
        await self.refresh_tokens.create(
            RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at)
        )
        return TokenPair(access_token=access_token, refresh_token=raw_refresh_token)

    async def refresh(self, raw_refresh_token: str) -> TokenPair:
        stored = await self.refresh_tokens.get_by_hash(hash_refresh_token(raw_refresh_token))
        if stored is None or stored.revoked or stored.expires_at < datetime.now(UTC):
            raise InvalidRefreshTokenError

        user = await self.users.get_by_id(stored.user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError

        # Rotation: the presented token is single-use — revoke it before
        # issuing its replacement so a leaked-but-already-used token can't
        # be replayed.
        await self.refresh_tokens.revoke(stored)
        return await self.issue_token_pair(user)

    async def logout(self, raw_refresh_token: str) -> None:
        stored = await self.refresh_tokens.get_by_hash(hash_refresh_token(raw_refresh_token))
        if stored is not None and not stored.revoked:
            await self.refresh_tokens.revoke(stored)

    async def get_or_create_oauth_user(
        self, provider: str, oauth_id: str, email: str, full_name: str
    ) -> User:
        user = await self.users.get_by_oauth(provider, oauth_id)
        if user is not None:
            return user

        # Link to an existing email/password account rather than creating a
        # duplicate identity for the same person.
        existing = await self.users.get_by_email(email)
        if existing is not None:
            existing.oauth_provider = provider
            existing.oauth_id = oauth_id
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        user = User(email=email, full_name=full_name, oauth_provider=provider, oauth_id=oauth_id)
        return await self.users.create(user)
