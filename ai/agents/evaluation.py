import re
from typing import Any, ClassVar

from ai.agents.base import BaseAgent
from ai.graph.state import ResearchState
from ai.llm.base import LLMMessage, LLMProvider

_SYSTEM_PROMPT = (
    "Score the following research report's quality on a scale from 0.0 to "
    "1.0, considering whether it answers the question, cites its sources, "
    "and is well-organized. Respond with ONLY a decimal number between 0 "
    "and 1 — no words, no explanation."
)

_NUMBER = re.compile(r"(\d*\.?\d+)")


def _parse_score(text: str) -> float:
    match = _NUMBER.search(text)
    if not match:
        return 0.0
    try:
        return max(0.0, min(1.0, float(match.group(1))))
    except ValueError:
        return 0.0


class EvaluationAgent(BaseAgent):
    name: ClassVar[str] = "evaluation"

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
                        f"Report:\n{state.get('draft_report', '')}"
                    ),
                ),
            ],
            temperature=0.0,
            max_tokens=20,  # see ai/agents/planner.py's comment on why this is capped
        )

        score = _parse_score(response.content)
        return {
            "quality_score": score,
            "current_node": self.name,
            "messages": [f"[{self.name}] scored {score:.2f}"],
            **self._llm_usage(response),
        }
