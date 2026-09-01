import uuid
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.document import Document

# Must match app.core.config.Settings.embedding_dimension (1024, BGE-large's
# native dimension). Changing embedding provider/model to a different
# dimension requires a new migration to alter this column.
EMBEDDING_DIMENSION = 1024


class Embedding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "embeddings"
    __table_args__ = (
        # Primary retrieval path (docs/database-schema.md § indexing strategy).
        # HNSW over IVFFlat: no training/list-count tuning needed and better
        # recall at the dataset sizes this project operates at.
        Index(
            "ix_embeddings_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=False)
    # Page number / section heading for citation traceability back to source
    # location. Column is named `metadata` in the DB; the ORM attribute is
    # renamed to avoid colliding with SQLAlchemy's reserved Base.metadata.
    chunk_metadata: Mapped[dict[str, object] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    document: Mapped["Document"] = relationship(back_populates="embeddings")
