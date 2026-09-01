"""Adapter binding ai.vectorstore.base.VectorStore's interface to a real
pgvector-backed EmbeddingRepository — gives the Retriever agent
(ai/agents/retriever.py) a real knowledge base to search. Lives here, not in
ai/, because it needs a live AsyncSession (ai/ stays DB-independent — see
ai/vectorstore/base.py's docstring).
"""

import uuid

from ai.graph.state import RetrievedChunk
from ai.vectorstore.base import VectorStore

from app.repositories.embedding import EmbeddingRepository


class PgVectorStore(VectorStore):
    def __init__(self, embeddings_repo: EmbeddingRepository) -> None:
        self._embeddings_repo = embeddings_repo

    async def similarity_search(
        self, query_embedding: list[float], *, project_id: str, top_k: int = 5
    ) -> list[RetrievedChunk]:
        pairs = await self._embeddings_repo.similarity_search(
            uuid.UUID(project_id), query_embedding, top_k=top_k
        )
        return [
            RetrievedChunk(
                document_id=str(embedding.document_id),
                chunk_index=embedding.chunk_index,
                chunk_text=embedding.chunk_text,
                score=1.0 - distance,
                metadata=embedding.chunk_metadata,
            )
            for embedding, distance in pairs
        ]
