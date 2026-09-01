import asyncio
from typing import Any, ClassVar

from ai.agents.base import BaseAgent
from ai.graph.state import ResearchState
from ai.tools.base import BaseTool


class ResearchAgent(BaseAgent):
    """Fans out to every injected tool concurrently and aggregates results.
    A tool that errors or rate-limits returns an empty list (see
    BaseTool.search's contract) rather than raising, so one flaky source
    doesn't fail the whole step.
    """

    name: ClassVar[str] = "research"

    def __init__(self, tools: list[BaseTool], *, max_results_per_tool: int = 5) -> None:
        self._tools = tools
        self._max_results_per_tool = max_results_per_tool

    async def __call__(self, state: ResearchState) -> dict[str, Any]:
        query = state["query"]
        results_per_tool = await asyncio.gather(
            *(tool.search(query, max_results=self._max_results_per_tool) for tool in self._tools)
        )
        findings = [finding for results in results_per_tool for finding in results]

        return {
            "research_findings": findings,
            "current_node": self.name,
            "messages": [
                f"[{self.name}] found {len(findings)} result(s) across "
                f"{len(self._tools)} tool(s): {', '.join(t.name for t in self._tools)}"
            ],
        }
