"""LLMProvider — the swappable-implementation boundary described in
docs/architecture.md § 5. Agents depend on this protocol, never on
`openai`/`anthropic`/`ollama` SDK types directly, so switching providers is a
`Settings.ai_provider` change, not a code change.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class LLMMessage:
    role: Role
    content: str


@dataclass(frozen=True)
class LLMResponse:
    """Real per-call token usage (Phase 11), as reported by each vendor's own
    API response — not estimated from text length — so
    app/workers/tasks.py can persist it (via each agent's returned dict,
    landing in AgentRun.output_state) for the Analytics Dashboard's
    token/cost usage view to aggregate over."""

    content: str
    prompt_tokens: int
    completion_tokens: int
    model: str


class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Returns the assistant's reply plus real token usage for the given
        message history."""
