import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.embedding import Embedding


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, document: Document) -> Document:
        self.session.add(document)
        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        return await self.session.get(Document, document_id)

    async def list_for_project(self, project_id: uuid.UUID) -> list[tuple[Document, int]]:
        """Returns (document, chunk_count) pairs — the KB browser UI shows
        each document's chunk count without a separate query per card."""
        chunk_count = func.count(Embedding.id)
        result = await self.session.execute(
            select(Document, chunk_count)
            .outerjoin(Embedding, Embedding.document_id == Document.id)
            .where(Document.project_id == project_id, Document.deleted_at.is_(None))
            .group_by(Document.id)
            .order_by(Document.created_at.desc())
        )
        return [(row[0], row[1]) for row in result.all()]

    async def soft_delete(self, document: Document) -> None:
        document.deleted_at = datetime.now(UTC)
        await self.session.commit()
