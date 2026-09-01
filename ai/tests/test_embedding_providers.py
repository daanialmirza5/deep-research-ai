"""OpenAI's embedding endpoint is verified against a mocked SDK client (no
API key available here). BGE is verified live — a real local model via
sentence-transformers — skipped automatically if the `local` extra isn't
installed (see backend/pyproject.toml's `[project.optional-dependencies]`;
only the worker image and a dev machine that opted in have it).
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from ai.embeddings.openai_provider import OpenAIEmbeddingProvider

pytestmark = pytest.mark.asyncio

try:
    import sentence_transformers  # noqa: F401

    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    _HAS_SENTENCE_TRANSFORMERS = False


async def test_openai_embedding_provider_maps_request_and_response() -> None:
    provider = OpenAIEmbeddingProvider(
        api_key="test-key", model="text-embedding-3-small", dimension=3
    )
    fake_response = MagicMock(
        data=[MagicMock(embedding=[0.1, 0.2, 0.3]), MagicMock(embedding=[0.4, 0.5, 0.6])]
    )
    provider._client.embeddings.create = AsyncMock(return_value=fake_response)  # type: ignore[method-assign]

    result = await provider.embed(["first", "second"])

    assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    _, kwargs = provider._client.embeddings.create.call_args
    assert kwargs["input"] == ["first", "second"]
    assert kwargs["model"] == "text-embedding-3-small"
    assert provider.dimension == 3


@pytest.mark.skipif(
    not _HAS_SENTENCE_TRANSFORMERS,
    reason="sentence-transformers not installed (only the `local` extra has it)",
)
async def test_bge_provider_live_embed_produces_normalized_vectors() -> None:
    from ai.embeddings.bge_provider import BGEProvider

    # A small, fast model for test speed — the app's real default
    # (BAAI/bge-large-en-v1.5, 1024-dim) is exercised manually/in the worker,
    # not downloaded fresh on every test run.
    provider = BGEProvider(model_name="BAAI/bge-small-en-v1.5", dimension=384)

    vectors = await provider.embed(["hello world", "another sentence"])

    assert len(vectors) == 2
    assert all(len(v) == 384 for v in vectors)
    # normalize_embeddings=True means every vector should be ~unit length.
    magnitude = sum(x * x for x in vectors[0]) ** 0.5
    assert abs(magnitude - 1.0) < 1e-3
