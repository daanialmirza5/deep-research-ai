import uuid
from typing import TYPE_CHECKING, Literal

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.embedding import Embedding
    from app.models.project import Project
    from app.models.user import User

DocumentSourceType = Literal["pdf", "docx", "txt", "csv", "markdown", "url", "youtube"]
DocumentStatus = Literal["pending", "processing", "indexed", "failed"]


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('pdf', 'docx', 'txt', 'csv', 'markdown', 'url', 'youtube')",
            name="source_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'indexed', 'failed')", name="status"
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[DocumentSourceType] = mapped_column(String(20), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # MinIO object key, not a local filesystem path — keeps storage swappable to S3.
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(String(20), nullable=False, default="pending")

    project: Mapped["Project"] = relationship(back_populates="documents")
    uploader: Mapped["User"] = relationship()
    embeddings: Mapped[list["Embedding"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )
