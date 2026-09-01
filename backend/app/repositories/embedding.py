import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.embedding import Embedding


class EmbeddingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_many(
        self,
        document_id: uuid.UUID,
        chunks: list[str],
        vectors: list[list[float]],
    ) -> list[Embedding]:
        rows = [
            Embedding(document_id=document_id, chunk_index=index, chunk_text=text, embedding=vector)
            for index, (text, vector) in enumerate(zip(chunks, vectors, strict=True))
        ]
        self.session.add_all(rows)
        await self.session.flush()
        return rows

    async def similarity_search(
        self, project_id: uuid.UUID, query_embedding: list[float], *, top_k: int = 5
    ) -> list[tuple[Embedding, float]]:
        """Returns (embedding, cosine_distance) pairs ordered by ascending
        distance (most similar first) — pgvector's `<=>` operator, scoped to
        the given project via a join on documents (soft-deleted documents
        excluded)."""
        distance = Embedding.embedding.cosine_distance(query_embedding)
        result = await self.session.execute(
            select(Embedding, distance.label("distance"))
            .join(Document, Document.id == Embedding.document_id)
            .where(Document.project_id == project_id, Document.deleted_at.is_(None))
            .order_by(distance)
            .limit(top_k)
        )
        return [(row[0], row[1]) for row in result.all()]
