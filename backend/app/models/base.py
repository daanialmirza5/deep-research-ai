"""Declarative base, naming convention, and shared column mixins.

The naming convention is what lets Alembic autogenerate stable, predictable
constraint/index names across migrations — without it, SQLAlchemy lets the
database pick names, which then drift between environments and make
autogenerate diffs noisy.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKeyMixin:
    """Client-generated UUIDv4 primary key — portable across backends and lets
    the application know a new row's id before INSERT, without depending on a
    Postgres-side UUID-generation extension."""

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """created_at/updated_at on every table, per docs/database-schema.md § 1.
    `onupdate` fires for ORM-issued UPDATEs; raw SQL bypassing the ORM won't
    refresh it — acceptable here since all writes go through SQLAlchemy."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """deleted_at on user-facing entities only (users, projects, sessions,
    documents, reports) per docs/database-schema.md § 1."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
