import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.research_session import ResearchSession

AgentRunStatus = Literal["queued", "running", "completed", "failed"]


class Agent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Reference table — one row per agent type (planner, research, retriever,
    summarizer, writer, reviewer, fact_checker, citation, memory, evaluation).
    Seeded once real agents exist (Phase 7); lets the Agent Monitor screen
    list/enable/configure agents without a schema change.
    """

    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # No delete cascade here on purpose: agent_runs.agent_id is ON DELETE
    # RESTRICT (an agent type with existing run history shouldn't be
    # deletable). passive_deletes=True stops SQLAlchemy from trying to NULL
    # the (NOT NULL) child FK before the parent delete — it just issues the
    # DELETE and lets Postgres's RESTRICT reject it when runs exist.
    runs: Mapped[list["AgentRun"]] = relationship(back_populates="agent", passive_deletes=True)


class AgentRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Append-only execution log per session per agent — source of truth for
    both the live Agent Workflow Visualization and historical analytics."""

    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')", name="status"
        ),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[AgentRunStatus] = mapped_column(String(20), nullable=False, default="queued")
    input_state: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    output_state: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped["ResearchSession"] = relationship(back_populates="agent_runs")
    agent: Mapped["Agent"] = relationship(back_populates="runs")
