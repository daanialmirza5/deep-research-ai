"""Every agent implements this so the graph (ai/graph/build.py) can wire new
agents in without touching how nodes are called — only the edges change.
See docs/architecture.md § 3.
"""

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from ai.graph.state import ResearchState
from ai.llm.base import LLMResponse


class BaseAgent(ABC):
    name: ClassVar[str]

    @abstractmethod
    async def __call__(self, state: ResearchState) -> dict[str, Any]:
        """Returns a partial state update; LangGraph merges it into
        ResearchState (see ai/graph/state.py's Annotated `operator.add`
        fields for which keys accumulate vs. overwrite)."""

    @staticmethod
    def _llm_usage(response: LLMResponse) -> dict[str, Any]:
        """Shared by every LLM-calling agent so real per-call token usage
        (Phase 11) lands in the node's own returned dict — and from there in
        AgentRun.output_state (app/workers/tasks.py) — without each agent
        repeating the same three keys. Overwritten each time a node runs
        (like `current_node`), not accumulated: the per-node AgentRun
        snapshot is what the Analytics Dashboard aggregates over, not the
        final merged state."""
        return {
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "llm_model": response.model,
        }
