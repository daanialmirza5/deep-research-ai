from typing import Any, ClassVar

from ai.agents.base import BaseAgent
from ai.graph.state import ResearchFinding, ResearchState
from ai.llm.base import LLMMessage, LLMProvider

_SYSTEM_PROMPT = (
    "You are the writing agent in a multi-agent research system. Write a "
    "well-organized markdown report answering the research question, using "
    "ONLY the provided sources. Cite sources inline like [1], [2], matching "
    "their position in the source list below. If revision feedback from a "
    "previous review is provided, address it directly. Do not fabricate "
    "facts, sources, or citations beyond what's given."
)


def _format_sources(findings: list[ResearchFinding]) -> str:
    if not findings:
        return "(no sources found)"
    return "\n".join(
        f"[{i + 1}] {f['title']} ({f['source']}): {f['snippet']}" for i, f in enumerate(findings)
    )


class WriterAgent(BaseAgent):
    name: ClassVar[str] = "writer"

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def __call__(self, state: ResearchState) -> dict[str, Any]:
        findings = state.get("research_findings", [])
        user_parts = [
            f"Question: {state['query']}",
            f"Summary: {state.get('summary', '')}",
            f"Sources:\n{_format_sources(findings)}",
        ]
        if state.get("review_feedback"):
            user_parts.append(
                "Revision feedback from a previous review — address this: "
                f"{state['review_feedback']}"
            )

        response = await self._llm.generate(
            [
                LLMMessage(role="system", content=_SYSTEM_PROMPT),
                LLMMessage(role="user", content="\n\n".join(user_parts)),
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        return {
            "draft_report": response.content,
            "current_node": self.name,
            "messages": [
                f"[{self.name}] drafted a {len(response.content)}-character report"
            ],
            **self._llm_usage(response),
        }
