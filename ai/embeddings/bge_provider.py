import asyncio
from collections.abc import Sequence

from sentence_transformers import SentenceTransformer

from ai.embeddings.base import EmbeddingProvider


class BGEProvider(EmbeddingProvider):
    """Local-first default: no API key, downloads/runs a BGE model via
    sentence-transformers. Only the worker image installs the `local` extra
    this needs (torch + sentence-transformers) — the lean API image never
    imports this module (see ai/embeddings/factory.py's deferred import and
    app/core/container.py's lazy `embeddings` property)."""

    def __init__(self, model_name: str, dimension: int) -> None:
        self._model = SentenceTransformer(model_name)
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        # sentence-transformers is sync/CPU-or-GPU-bound; offload so it
        # doesn't block the event loop other agents/requests share.
        # normalize_embeddings=True matches BGE's intended usage and the
        # vector_cosine_ops HNSW index on embeddings.embedding (Phase 4).
        embeddings = await asyncio.to_thread(
            self._model.encode, list(texts), normalize_embeddings=True
        )
        return embeddings.tolist()  # type: ignore[no-any-return]
