from typing import Any, ClassVar

from ai.agents.base import BaseAgent
from ai.graph.state import ResearchState
from ai.llm.base import LLMMessage, LLMProvider

_SYSTEM_PROMPT = (
    "You are the planning agent in a multi-agent research system. Given a "
    "research question, produce a short (3-5 step) plan for how to research "
    "it. Be concise — one line per step."
)


class PlannerAgent(BaseAgent):
    """Real LLM call (this is genuinely live, not a stub passthrough) but a
    deliberately simple prompt — richer planning (source prioritization,
    sub-question decomposition) is Phase 8, once Research/Retriever have
    real tools to plan against."""

    name: ClassVar[str] = "planner"

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def __call__(self, state: ResearchState) -> dict[str, Any]:
        response = await self._llm.generate(
            [
                LLMMessage(role="system", content=_SYSTEM_PROMPT),
                LLMMessage(role="user", content=state["query"]),
            ],
            temperature=0.2,
            # Local/small models don't reliably stop on their own; without a
            # cap a live run against Ollama was observed generating for 30+
            # minutes on one call instead of the expected few short lines.
            max_tokens=300,
        )
        return {
            "plan": response.content,
            "current_node": self.name,
            "messages": [
                f"[{self.name}] produced a {len(response.content.splitlines())}-line plan"
            ],
            **self._llm_usage(response),
        }
