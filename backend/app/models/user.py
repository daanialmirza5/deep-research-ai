from typing import TYPE_CHECKING, Literal

from sqlalchemy import Boolean, CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.auth import ApiKey, RefreshToken
    from app.models.project import Project

UserRole = Literal["admin", "member"]


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('admin', 'member')", name="role"),)

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String, nullable=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    oauth_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    oauth_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(String(20), nullable=False, default="member")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # cascade + passive_deletes: the FK columns below are NOT NULL with
    # ON DELETE CASCADE at the DB level (see e.g. Project.owner_id); without
    # this, SQLAlchemy's default behavior is to try to NULL the child's FK
    # before deleting the parent, which fails against a NOT NULL column.
    # passive_deletes=True defers the actual cascade to the database instead
    # of SQLAlchemy loading and deleting each child row itself.
    projects: Mapped[list["Project"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    api_keys: Mapped[list["ApiKey"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
