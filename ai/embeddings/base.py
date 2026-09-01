"""EmbeddingProvider — the swappable-implementation boundary for turning
text into vectors (see docs/architecture.md § 5). Retriever/Memory agents
depend on this protocol, never on `sentence_transformers`/`openai` directly.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector width this provider produces — must match the target
        pgvector column (see app/models/embedding.py's EMBEDDING_DIMENSION)."""

    @abstractmethod
    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Returns one embedding vector per input text, same order."""
