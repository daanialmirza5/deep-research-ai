from abc import ABC, abstractmethod

from ai.graph.state import RetrievedChunk


class VectorStore(ABC):
    """Similarity search over a project's embedded knowledge base. The
    concrete implementation (pgvector, Phase 9) lives in the backend, not
    here — it needs a live DB session, and ai/ stays independent of any
    backend/database dependency (see docs/architecture.md's clean-architecture
    layering). Constructed and injected the same way ai/tools/base.py's
    BaseTool is: the caller builds the concrete store and hands it to
    build_research_graph(), ai/ never reaches for one itself.
    """

    @abstractmethod
    async def similarity_search(
        self, query_embedding: list[float], *, project_id: str, top_k: int = 5
    ) -> list[RetrievedChunk]:
        """Returns up to top_k chunks ranked by similarity (highest score
        first). Must not raise on an empty/unindexed project — return an
        empty list instead."""
