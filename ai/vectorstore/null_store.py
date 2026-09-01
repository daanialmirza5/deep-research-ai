from ai.graph.state import RetrievedChunk
from ai.vectorstore.base import VectorStore


class NullVectorStore(VectorStore):
    """Always returns no results. The default when a caller doesn't provide a
    real VectorStore (tests, or any graph run where wiring one up isn't the
    point) — better than requiring every build_research_graph() caller to
    supply one."""

    async def similarity_search(
        self, query_embedding: list[float], *, project_id: str, top_k: int = 5
    ) -> list[RetrievedChunk]:
        return []
