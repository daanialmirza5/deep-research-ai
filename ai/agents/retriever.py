from typing import Any, ClassVar

from ai.agents.base import BaseAgent
from ai.embeddings.base import EmbeddingProvider
from ai.graph.state import ResearchState
from ai.vectorstore.base import VectorStore


class RetrieverAgent(BaseAgent):
    """Embeds the query, then runs a real similarity search against the
    project's knowledge base (ai/vectorstore/) — the vector store itself is
    injected, not constructed here, so ai/ stays independent of the pgvector
    implementation (backend-only, needs a live DB session)."""

    name: ClassVar[str] = "retriever"

    def __init__(self, embeddings: EmbeddingProvider, vector_store: VectorStore) -> None:
        self._embeddings = embeddings
        self._vector_store = vector_store

    async def __call__(self, state: ResearchState) -> dict[str, Any]:
        [query_vector] = await self._embeddings.embed([state["query"]])
        chunks = await self._vector_store.similarity_search(
            query_vector, project_id=state["project_id"], top_k=5
        )
        return {
            "retrieved_context": chunks,
            "current_node": self.name,
            "messages": [
                f"[{self.name}] retrieved {len(chunks)} chunk(s) from the knowledge base"
            ],
        }
