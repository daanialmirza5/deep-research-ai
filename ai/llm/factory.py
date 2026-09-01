"""Selects the configured LLMProvider implementation. The only place in the
codebase that imports all three vendor SDKs — everything downstream depends
on `LLMProvider`, not on which branch fired here.
"""

from typing import Protocol

from ai.llm.base import LLMProvider


class _LLMSettings(Protocol):
    ai_provider: str
    openai_api_key: str
    openai_model: str
    anthropic_api_key: str
    anthropic_model: str
    ollama_base_url: str
    ollama_model: str


def get_llm_provider(settings: _LLMSettings) -> LLMProvider:
    if settings.ai_provider == "openai":
        from ai.llm.openai_provider import OpenAIProvider

        return OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model)

    if settings.ai_provider == "anthropic":
        from ai.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(api_key=settings.anthropic_api_key, model=settings.anthropic_model)

    if settings.ai_provider == "ollama":
        from ai.llm.ollama_provider import OllamaProvider

        return OllamaProvider(base_url=settings.ollama_base_url, model=settings.ollama_model)

    raise ValueError(f"Unknown AI_PROVIDER: {settings.ai_provider!r}")
