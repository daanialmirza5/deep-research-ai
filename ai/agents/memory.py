from typing import Any, ClassVar

from ai.agents.base import BaseAgent
from ai.graph.state import ResearchState


class MemoryAgent(BaseAgent):
    """Stub: persisting the finished session to the long-term knowledge base
    (ai/memory/) lands in Phase 9/10, once there's a vector store to write
    to. This is the graph's terminal node."""

    name: ClassVar[str] = "memory"

    async def __call__(self, state: ResearchState) -> dict[str, Any]:
        return {
            "current_node": self.name,
            "messages": [f"[{self.name}] stub — nothing persisted yet"],
        }
