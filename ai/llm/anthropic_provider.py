from typing import cast

from anthropic import AsyncAnthropic, omit
from anthropic.types import MessageParam

from ai.llm.base import LLMMessage, LLMProvider, LLMResponse

_DEFAULT_MAX_TOKENS = 1024  # Anthropic's Messages API has no default, unlike OpenAI's.


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        # Anthropic's API takes the system prompt separately from the
        # messages list, unlike OpenAI/Ollama's role="system" convention.
        system = "\n".join(m.content for m in messages if m.role == "system")
        turns = cast(
            list[MessageParam],
            [{"role": m.role, "content": m.content} for m in messages if m.role != "system"],
        )

        response = await self._client.messages.create(
            model=self._model,
            # `system` only accepts str | Iterable[TextBlockParam] | Omit — not
            # None — so an empty prompt uses the SDK's own "not provided" sentinel.
            system=system if system else omit,
            messages=turns,
            temperature=temperature,
            max_tokens=max_tokens or _DEFAULT_MAX_TOKENS,
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return LLMResponse(
            content=text,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            model=self._model,
        )
