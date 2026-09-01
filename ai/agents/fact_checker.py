from typing import Any, ClassVar, Literal

from ai.agents.base import BaseAgent
from ai.graph.state import ResearchState
from ai.llm.base import LLMMessage, LLMProvider

_SYSTEM_PROMPT = (
    "You are a fact-checking agent in a multi-agent research system. Given a "
    "research question and a summary of gathered sources, decide whether the "
    "sources are sufficient to answer the question. Respond with exactly one "
    "word first — VERIFIED or UNVERIFIED — optionally followed by a colon and "
    "a one-sentence reason."
)


class FactCheckerAgent(BaseAgent):
    name: ClassVar[str] = "fact_checker"

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def __call__(self, state: ResearchState) -> dict[str, Any]:
        findings = state.get("research_findings", [])
        if not findings:
            # No evidence at all — an unambiguous case, not worth an LLM call.
            # route_after_fact_check (ai/graph/routing.py) sends this back to
            # Research if under the revision cap. IMPORTANT: revision_count
            # must be bumped here — routing.py only *reads* the cap, nothing
            # increments it otherwise (a real Phase 8 bug: without this, an
            # unverified verdict loops back to Research forever, since the
            # cap check `revision_count < max_revision_loops` never becomes
            # false).
            return {
                "fact_check_verdict": "unverified",
                "fact_check_notes": "no research findings gathered yet",
                "revision_count": state.get("revision_count", 0) + 1,
                "current_node": self.name,
                "messages": [f"[{self.name}] unverified — no findings to check"],
            }

        response = await self._llm.generate(
            [
                LLMMessage(role="system", content=_SYSTEM_PROMPT),
                LLMMessage(
                    role="user",
                    content=f"Question: {state['query']}\n\nSummary: {state.get('summary', '')}",
                ),
            ],
            temperature=0.0,
            max_tokens=150,  # see ai/agents/planner.py's comment on why this is capped
        )

        verdict: Literal["verified", "unverified"] = (
            "verified" if response.content.strip().upper().startswith("VERIFIED") else "unverified"
        )
        update: dict[str, Any] = {
            "fact_check_verdict": verdict,
            "fact_check_notes": response.content,
            "current_node": self.name,
            "messages": [f"[{self.name}] {verdict}"],
            **self._llm_usage(response),
        }
        if verdict == "unverified":
            update["revision_count"] = state.get("revision_count", 0) + 1
        return update
