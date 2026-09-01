from typing import Any, ClassVar

from ai.agents.base import BaseAgent
from ai.graph.state import ResearchState


class CitationAgent(BaseAgent):
    """Deterministic — no LLM call needed. Citations are built directly from
    research_findings' source metadata, in the same order Writer numbered
    them, so [1]/[2] markers in the draft line up with these entries."""

    name: ClassVar[str] = "citation"

    async def __call__(self, state: ResearchState) -> dict[str, Any]:
        findings = state.get("research_findings", [])
        citations = [
            {"source_type": f["source"], "title": f["title"], "url": f["url"]} for f in findings
        ]
        return {
            "citations": citations,
            "current_node": self.name,
            "messages": [f"[{self.name}] generated {len(citations)} citation(s)"],
        }
