import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.research_session import ResearchSession
    from app.models.user import User


class AnalyticsEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Generic event log the Analytics Dashboard aggregates over. Kept
    generic (event_type + JSONB payload) rather than one table per metric so
    new metrics don't require migrations. user_id/session_id are nullable
    with ON DELETE SET NULL so analytics history survives account/session
    deletion.
    """

    __tablename__ = "analytics_events"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("research_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)

    user: Mapped["User | None"] = relationship()
    session: Mapped["ResearchSession | None"] = relationship(back_populates="analytics_events")
