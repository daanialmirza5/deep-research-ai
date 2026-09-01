import uuid
from typing import TYPE_CHECKING, Literal

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.research_session import ResearchSession
    from app.models.user import User

ProjectStatus = Literal["active", "archived"]


class Project(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "projects"
    __table_args__ = (CheckConstraint("status IN ('active', 'archived')", name="status"),)

    owner_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(String(20), nullable=False, default="active")

    owner: Mapped["User"] = relationship(back_populates="projects")
    research_sessions: Mapped[list["ResearchSession"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
