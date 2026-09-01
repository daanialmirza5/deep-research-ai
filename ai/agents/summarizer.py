from typing import Any, ClassVar

from ai.agents.base import BaseAgent
from ai.graph.state import ResearchFinding, ResearchState, RetrievedChunk
from ai.llm.base import LLMMessage, LLMProvider

_SYSTEM_PROMPT = (
    "You compress raw search results into a concise research summary for "
    "another agent to work from. Given a research question and a list of "
    "source snippets, write a 3-6 sentence summary of what they collectively "
    "say. Use only the provided snippets — do not add outside knowledge or "
    "invent details not present in them."
)


def _format_sources(findings: list[ResearchFinding]) -> str:
    return "\n\n".join(
        f"[{i + 1}] {f['title']} ({f['source']}): {f['snippet']}" for i, f in enumerate(findings)
    )


def _format_context(chunks: list[RetrievedChunk]) -> str:
    return "\n\n".join(f"[KB {i + 1}] {c['chunk_text']}" for i, c in enumerate(chunks))


class SummarizerAgent(BaseAgent):
    name: ClassVar[str] = "summarizer"

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def __call__(self, state: ResearchState) -> dict[str, Any]:
        findings = state.get("research_findings", [])
        chunks = state.get("retrieved_context", [])
        if not findings and not chunks:
            return {
                "summary": "",
                "current_node": self.name,
                "messages": [f"[{self.name}] no findings to summarize"],
            }

        user_parts = [f"Question: {state['query']}"]
        if findings:
            user_parts.append(f"Web/Arxiv/Wikipedia sources:\n{_format_sources(findings)}")
        if chunks:
            user_parts.append(f"Knowledge base excerpts:\n{_format_context(chunks)}")

        response = await self._llm.generate(
            [
                LLMMessage(role="system", content=_SYSTEM_PROMPT),
                LLMMessage(role="user", content="\n\n".join(user_parts)),
            ],
            temperature=0.2,
            max_tokens=600,  # see planner.py's comment on why this is capped
        )
        return {
            "summary": response.content,
            "current_node": self.name,
            "messages": [
                f"[{self.name}] summarized {len(findings)} finding(s) and "
                f"{len(chunks)} knowledge-base chunk(s)"
            ],
            **self._llm_usage(response),
        }
