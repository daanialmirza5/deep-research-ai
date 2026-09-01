"""In-memory fakes for LLMProvider/EmbeddingProvider/BaseTool/VectorStore —
used across ai/tests so agent/graph tests run fast and offline, independent
of the live-provider tests (test_llm_providers.py, test_embedding_providers.py,
test_live_ollama.py)."""

from collections.abc import Callable, Sequence

from ai.embeddings.base import EmbeddingProvider
from ai.graph.state import ResearchFinding, RetrievedChunk
from ai.llm.base import LLMMessage, LLMProvider, LLMResponse
from ai.tools.base import BaseTool
from ai.vectorstore.base import VectorStore

ResponseFn = Callable[[list[LLMMessage]], str]


class FakeLLMProvider(LLMProvider):
    """`response` may be a fixed string (fine for single-call agent tests)
    or a function of the message history (needed for a full-graph test,
    where several agents share one provider instance and each expects a
    different kind of reply — dispatch on each agent's distinct system
    prompt, the only thing that tells them apart from the fake's side).
    Token counts are fixed, fake values (10/5) — no real provider is called,
    so there's nothing real to report; tests that care about usage plumbing
    assert against these known constants rather than the LLMResponse text."""

    FAKE_PROMPT_TOKENS = 10
    FAKE_COMPLETION_TOKENS = 5

    def __init__(self, response: str | ResponseFn = "fake response") -> None:
        self._response = response
        self.calls: list[list[LLMMessage]] = []

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        self.calls.append(messages)
        content = self._response(messages) if callable(self._response) else self._response
        return LLMResponse(
            content=content,
            prompt_tokens=self.FAKE_PROMPT_TOKENS,
            completion_tokens=self.FAKE_COMPLETION_TOKENS,
            model="fake-model",
        )


class FakeEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dimension: int = 8) -> None:
        self._dimension = dimension
        self.calls: list[list[str]] = []

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [[0.1] * self._dimension for _ in texts]


class FakeTool(BaseTool):
    name = "fake_tool"

    def __init__(self, results: list[ResearchFinding] | None = None) -> None:
        self._results = (
            results
            if results is not None
            else [
                ResearchFinding(
                    source="fake_tool",
                    title="Fake Result",
                    url="https://example.com",
                    snippet="A fake snippet.",
                )
            ]
        )
        self.calls: list[str] = []

    async def search(self, query: str, *, max_results: int = 5) -> list[ResearchFinding]:
        self.calls.append(query)
        return self._results[:max_results]


class FakeVectorStore(VectorStore):
    def __init__(self, results: list[RetrievedChunk] | None = None) -> None:
        self._results = (
            results
            if results is not None
            else [
                RetrievedChunk(
                    document_id="fake-doc",
                    chunk_index=0,
                    chunk_text="A fake chunk from the knowledge base.",
                    score=0.9,
                    metadata=None,
                )
            ]
        )
        self.calls: list[tuple[list[float], str, int]] = []

    async def similarity_search(
        self, query_embedding: list[float], *, project_id: str, top_k: int = 5
    ) -> list[RetrievedChunk]:
        self.calls.append((query_embedding, project_id, top_k))
        return self._results[:top_k]
