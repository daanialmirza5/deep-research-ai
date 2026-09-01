import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.agent import AgentRun
    from app.models.analytics_event import AnalyticsEvent
    from app.models.message import Message
    from app.models.project import Project
    from app.models.report import Report
    from app.models.search_query import SearchQuery
    from app.models.user import User

SessionStatus = Literal["queued", "running", "awaiting_revision", "completed", "failed"]


class ResearchSession(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "research_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'awaiting_revision', 'completed', 'failed')",
            name="status",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SessionStatus] = mapped_column(String(30), nullable=False, default="queued")
    # Last checkpointed LangGraph state (Phase 7+); powers resume + the Agent
    # Workflow Visualization screen. See docs/architecture.md § 2.
    graph_state: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    revision_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="research_sessions")
    user: Mapped["User"] = relationship()
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    agent_runs: Mapped[list["AgentRun"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    reports: Mapped[list["Report"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    search_queries: Mapped[list["SearchQuery"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    # session_id is nullable with ON DELETE SET NULL (analytics history
    # should survive session deletion) — passive_deletes defers to the DB
    # instead of the ORM nulling each row individually.
    analytics_events: Mapped[list["AnalyticsEvent"]] = relationship(
        back_populates="session", passive_deletes=True
    )
