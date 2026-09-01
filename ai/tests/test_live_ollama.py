"""Real, live LLM call — no mocks. Skipped automatically (not opt-in) when
no local Ollama server is reachable, since unlike the Postgres integration
tests this needs nothing provisioned: Ollama is free, local, and either
running or it isn't. This is the "at least one provider live" proof for
Phase 7's exit criteria.
"""

import os

import httpx
import pytest

from ai.llm.base import LLMMessage
from ai.llm.ollama_provider import OllamaProvider

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")


def _ollama_reachable() -> bool:
    try:
        response = httpx.get(f"{OLLAMA_BASE_URL}/api/version", timeout=1.0)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


_SKIP_REASON = f"no Ollama server reachable at {OLLAMA_BASE_URL}"

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not _ollama_reachable(), reason=_SKIP_REASON),
]


async def test_ollama_provider_live_generate() -> None:
    provider = OllamaProvider(base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL)

    reply = await provider.generate(
        [
            LLMMessage(role="system", content="Reply with exactly one word and nothing else."),
            LLMMessage(role="user", content="Reply with the word: PONG"),
        ],
        temperature=0.0,
    )

    assert isinstance(reply.content, str)
    assert len(reply.content.strip()) > 0
    # Real per-call token counts (Phase 11) — Ollama reports these itself,
    # not estimated from text length.
    assert reply.prompt_tokens > 0
    assert reply.completion_tokens > 0
    assert reply.model == OLLAMA_MODEL
