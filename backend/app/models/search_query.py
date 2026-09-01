import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.research_session import ResearchSession


class SearchQuery(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Full audit trail of every external search call — debugging agent
    behavior and backing the Search History UI feature."""

    __tablename__ = "search_queries"

    session_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_results: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    session: Mapped["ResearchSession"] = relationship(back_populates="search_queries")
