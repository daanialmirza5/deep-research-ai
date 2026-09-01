import asyncio
from typing import ClassVar

import arxiv

from ai.graph.state import ResearchFinding
from ai.tools.base import BaseTool


class ArxivTool(BaseTool):
    """Academic paper search via Arxiv's public API. No API key required."""

    name: ClassVar[str] = "arxiv"

    def __init__(self) -> None:
        self._client = arxiv.Client()

    async def search(self, query: str, *, max_results: int = 5) -> list[ResearchFinding]:
        def _search_sync() -> list[arxiv.Result]:
            search = arxiv.Search(query=query, max_results=max_results)
            return list(self._client.results(search))

        try:
            results = await asyncio.to_thread(_search_sync)
        except arxiv.ArxivError:
            return []

        return [
            ResearchFinding(
                source=self.name,
                title=r.title,
                url=r.entry_id,
                snippet=r.summary.replace("\n", " ")[:500],
            )
            for r in results
        ]
