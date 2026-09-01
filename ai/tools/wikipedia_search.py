import re
from typing import ClassVar

import httpx

from ai.graph.state import ResearchFinding
from ai.tools.base import BaseTool

_SEARCH_URL = "https://en.wikipedia.org/w/api.php"
_HTML_TAG = re.compile(r"<[^>]+>")

# Wikipedia's API rejects requests without a descriptive User-Agent (see
# https://meta.wikimedia.org/wiki/User-Agent_policy) — a bare httpx.get()
# here returns 403, which is exactly what happened during Phase 8
# development before this header was added.
_USER_AGENT = "DeepResearchAI/0.1 (educational research project; no contact URL configured)"


class WikipediaTool(BaseTool):
    """Encyclopedic background search via Wikipedia's public search API. No
    API key required."""

    name: ClassVar[str] = "wikipedia"

    async def search(self, query: str, *, max_results: int = 5) -> list[ResearchFinding]:
        params: dict[str, str | int] = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": max_results,
            "format": "json",
        }
        headers = {"User-Agent": _USER_AGENT}
        try:
            async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
                response = await client.get(_SEARCH_URL, params=params)
                response.raise_for_status()
        except httpx.HTTPError:
            return []

        results = response.json().get("query", {}).get("search", [])
        return [
            ResearchFinding(
                source=self.name,
                title=item["title"],
                url=f"https://en.wikipedia.org/wiki/{item['title'].replace(' ', '_')}",
                snippet=_HTML_TAG.sub("", item.get("snippet", "")),
            )
            for item in results
        ]
