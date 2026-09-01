from typing import cast

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from ai.llm.base import LLMMessage, LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        # mypy can't narrow a plain {"role": ..., "content": ...} dict comprehension
        # into OpenAI's per-role TypedDict union — role is a runtime string, not a
        # literal at this point. The values are exactly LLMMessage.Role's members
        # ("system"/"user"/"assistant"), a subset of what the SDK accepts, so this
        # cast reflects a real invariant rather than papering over a mismatch.
        openai_messages = cast(
            list[ChatCompletionMessageParam],
            [{"role": m.role, "content": m.content} for m in messages],
        )
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        usage = response.usage
        return LLMResponse(
            content=response.choices[0].message.content or "",
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            model=self._model,
        )
