from ollama import AsyncClient

from ai.llm.base import LLMMessage, LLMProvider, LLMResponse


class OllamaProvider(LLMProvider):
    """The fully-local path: no API key, runs against a local/self-hosted
    Ollama server (see docker-compose.yml's opt-in `ollama` service, profile
    `local-ai`)."""

    def __init__(self, base_url: str, model: str) -> None:
        self._client = AsyncClient(host=base_url)
        self._model = model

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        options = {"temperature": temperature}
        if max_tokens:
            options["num_predict"] = max_tokens

        response = await self._client.chat(
            model=self._model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            options=options,
        )
        return LLMResponse(
            content=response["message"]["content"] or "",
            # Ollama's own token-accounting fields — real counts from the
            # local model runtime, not estimated.
            prompt_tokens=response.get("prompt_eval_count") or 0,
            completion_tokens=response.get("eval_count") or 0,
            model=self._model,
        )
