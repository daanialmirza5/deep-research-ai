"""Async SQLAlchemy engine + session factory construction. Kept free of any
dependency on app.core.container so the two modules can import in one
direction only (container -> db); request-scoped session retrieval lives in
app/api/deps.py instead, to avoid a container <-> db import cycle.
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, pool_pre_ping=True, echo=False)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
