from typing import Any, ClassVar

from ai.agents.base import BaseAgent
from ai.graph.state import ResearchState
from ai.llm.base import LLMMessage, LLMProvider

_SYSTEM_PROMPT = (
    "You are a reviewing agent in a multi-agent research system. Critique the "
    "draft report for accuracy against its sources, clarity, and whether it "
    "actually answers the question. Respond with exactly APPROVED if it's "
    "good enough to publish, or REVISE: <specific, actionable feedback> if it "
    "needs work."
)


class ReviewerAgent(BaseAgent):
    name: ClassVar[str] = "reviewer"

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def __call__(self, state: ResearchState) -> dict[str, Any]:
        response = await self._llm.generate(
            [
                LLMMessage(role="system", content=_SYSTEM_PROMPT),
                LLMMessage(
                    role="user",
                    content=(
                        f"Question: {state['query']}\n\n"
                        f"Draft:\n{state.get('draft_report', '')}"
                    ),
                ),
            ],
            temperature=0.0,
            max_tokens=500,  # see ai/agents/planner.py's comment on why this is capped
        )

        approved = response.content.strip().upper().startswith("APPROVED")
        update: dict[str, Any] = {
            "review_approved": approved,
            "review_feedback": "" if approved else response.content,
            "current_node": self.name,
            "messages": [f"[{self.name}] {'approved' if approved else 'requested revision'}"],
            **self._llm_usage(response),
        }
        if not approved:
            # See fact_checker.py's comment: routing.py only reads the
            # revision cap, the agent that fails its gate must bump it.
            update["revision_count"] = state.get("revision_count", 0) + 1
        return update
