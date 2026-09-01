"""OpenAI/Anthropic have no credentials available in dev/CI here, so these
verify request-shaping and response-parsing against a mocked SDK client
(the actual network boundary) rather than a live call. Ollama's live check
lives in test_live_ollama.py, gated on the server actually being reachable
— free and local, so no API-key gate needed the way Postgres integration
tests (backend/tests/integration/) require an explicit opt-in.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from ai.llm.anthropic_provider import AnthropicProvider
from ai.llm.base import LLMMessage
from ai.llm.openai_provider import OpenAIProvider

pytestmark = pytest.mark.asyncio


async def test_openai_provider_maps_messages_and_extracts_reply() -> None:
    provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")
    fake_response = MagicMock(
        choices=[MagicMock(message=MagicMock(content="hello from openai"))],
        usage=MagicMock(prompt_tokens=12, completion_tokens=4),
    )
    provider._client.chat.completions.create = AsyncMock(return_value=fake_response)  # type: ignore[method-assign]

    reply = await provider.generate([LLMMessage(role="user", content="hi")], temperature=0.5)

    assert reply.content == "hello from openai"
    assert reply.prompt_tokens == 12
    assert reply.completion_tokens == 4
    assert reply.model == "gpt-4o-mini"
    _, kwargs = provider._client.chat.completions.create.call_args
    assert kwargs["messages"] == [{"role": "user", "content": "hi"}]
    assert kwargs["temperature"] == 0.5
    assert kwargs["model"] == "gpt-4o-mini"


async def test_anthropic_provider_separates_system_prompt_and_extracts_text() -> None:
    provider = AnthropicProvider(api_key="test-key", model="claude-haiku-4-5-20251001")
    fake_response = MagicMock(
        content=[MagicMock(type="text", text="hello from anthropic")],
        usage=MagicMock(input_tokens=20, output_tokens=8),
    )
    provider._client.messages.create = AsyncMock(return_value=fake_response)  # type: ignore[method-assign]

    reply = await provider.generate(
        [
            LLMMessage(role="system", content="be terse"),
            LLMMessage(role="user", content="hi"),
        ]
    )

    assert reply.content == "hello from anthropic"
    assert reply.prompt_tokens == 20
    assert reply.completion_tokens == 8
    assert reply.model == "claude-haiku-4-5-20251001"
    _, kwargs = provider._client.messages.create.call_args
    assert kwargs["system"] == "be terse"
    assert kwargs["messages"] == [{"role": "user", "content": "hi"}]
    assert kwargs["max_tokens"] == 1024
