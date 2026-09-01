from collections.abc import Sequence

from openai import AsyncOpenAI

from ai.embeddings.base import EmbeddingProvider


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str, dimension: int) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(model=self._model, input=list(texts))
        return [item.embedding for item in response.data]
