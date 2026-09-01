import asyncio
from typing import ClassVar

from ddgs import DDGS
from ddgs.exceptions import DDGSException

from ai.graph.state import ResearchFinding
from ai.tools.base import BaseTool


class DuckDuckGoTool(BaseTool):
    """General web search. No API key required. `ddgs` (the package
    duckduckgo-search was renamed to) is a sync client, so calls are
    offloaded to a thread to avoid blocking the event loop other agents
    share — same pattern as ai/embeddings/bge_provider.py.
    """

    name: ClassVar[str] = "duckduckgo"

    async def search(self, query: str, *, max_results: int = 5) -> list[ResearchFinding]:
        try:
            results = await asyncio.to_thread(
                lambda: DDGS().text(query, max_results=max_results)
            )
        except DDGSException:
            return []

        return [
            ResearchFinding(
                source=self.name,
                title=r.get("title", ""),
                url=r.get("href", ""),
                snippet=r.get("body", ""),
            )
            for r in results or []
        ]
