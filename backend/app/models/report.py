import uuid
from typing import TYPE_CHECKING, Literal

from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.research_session import ResearchSession

ReportStatus = Literal["draft", "approved", "superseded"]
CitationStyle = Literal["apa", "mla", "ieee"]
ExportFormat = Literal["markdown", "pdf", "docx", "html"]


class Report(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'approved', 'superseded')", name="status"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[ReportStatus] = mapped_column(String(20), nullable=False, default="draft")
    # Increments on every Reviewer-triggered revision — history is retained,
    # not overwritten (see docs/database-schema.md § reports).
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    session: Mapped["ResearchSession"] = relationship(back_populates="reports")
    citations: Mapped[list["Citation"]] = relationship(
        back_populates="report", cascade="all, delete-orphan", passive_deletes=True
    )
    exports: Mapped[list["ReportExport"]] = relationship(
        back_populates="report", cascade="all, delete-orphan", passive_deletes=True
    )


class Citation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "citations"
    __table_args__ = (
        CheckConstraint("citation_style IN ('apa', 'mla', 'ieee')", name="citation_style"),
    )

    report_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    authors: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    doi: Mapped[str | None] = mapped_column(String(200), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    citation_style: Mapped[CitationStyle] = mapped_column(String(10), nullable=False, default="apa")
    formatted_citation: Mapped[str | None] = mapped_column(Text, nullable=True)

    report: Mapped["Report"] = relationship(back_populates="citations")


class ReportExport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "report_exports"
    __table_args__ = (
        CheckConstraint("format IN ('markdown', 'pdf', 'docx', 'html')", name="format"),
    )

    report_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    format: Mapped[ExportFormat] = mapped_column(String(20), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)

    report: Mapped["Report"] = relationship(back_populates="exports")
