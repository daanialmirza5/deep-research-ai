"""Selects the configured EmbeddingProvider implementation. Both branches
import their concrete provider lazily (inside the `if`, not at module top
level) so importing this factory module — which app/core/container.py's
`embeddings` property does unconditionally — never pulls in
sentence-transformers/torch. Only actually calling `get_embedding_provider()`
with `embedding_provider="bge"` does, which only ever happens in the worker
image (see docker/worker/Dockerfile's `local` extra).
"""

from typing import Protocol

from ai.embeddings.base import EmbeddingProvider


class _EmbeddingSettings(Protocol):
    embedding_provider: str
    embedding_dimension: int
    bge_model_name: str
    openai_api_key: str
    openai_embedding_model: str


def get_embedding_provider(settings: _EmbeddingSettings) -> EmbeddingProvider:
    if settings.embedding_provider == "bge":
        from ai.embeddings.bge_provider import BGEProvider

        return BGEProvider(
            model_name=settings.bge_model_name, dimension=settings.embedding_dimension
        )

    if settings.embedding_provider == "openai":
        from ai.embeddings.openai_provider import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            dimension=settings.embedding_dimension,
        )

    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {settings.embedding_provider!r}")
