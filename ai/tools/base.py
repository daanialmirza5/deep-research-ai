"""BaseTool — the swappable-implementation boundary for search sources (see
docs/architecture.md's replaceability matrix). The Research agent depends on
a list of these, never on a specific search SDK.
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from ai.graph.state import ResearchFinding


class BaseTool(ABC):
    name: ClassVar[str]

    @abstractmethod
    async def search(self, query: str, *, max_results: int = 5) -> list[ResearchFinding]:
        """Returns up to `max_results` findings. Must not raise on ordinary
        "no results"/rate-limit conditions — return an empty list instead,
        so one flaky source doesn't take down the whole Research step."""
