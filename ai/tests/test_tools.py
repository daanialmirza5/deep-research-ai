"""Live tests — real network calls to each free, no-API-key search source.
No dedicated reachability gate (unlike test_live_ollama.py, there's no
single "is the service up" endpoint to probe for three different
providers): each tool already swallows errors and returns `[]` per
BaseTool's contract, so an empty result here is treated as "couldn't reach
it right now" and skipped rather than failed, keeping the suite from being
flaky on a bad network day without hiding a real regression (a genuine bug
would fail the shape assertions on the results that DO come back on a
working run — this test was in fact run successfully during Phase 8
development).
"""

from collections.abc import Sequence

import pytest

from ai.tools.arxiv_search import ArxivTool
from ai.tools.web_search import DuckDuckGoTool
from ai.tools.wikipedia_search import WikipediaTool

pytestmark = pytest.mark.asyncio


def _assert_valid_findings(findings: Sequence[object], expected_source: str) -> None:
    for finding in findings:
        assert isinstance(finding, dict)
        assert finding["source"] == expected_source
        assert finding["title"]
        assert finding["url"].startswith("http")


async def test_duckduckgo_tool_live_search() -> None:
    results = await DuckDuckGoTool().search("retrieval augmented generation", max_results=3)
    if not results:
        pytest.skip("no results — DuckDuckGo unreachable or rate-limited right now")
    assert len(results) <= 3
    _assert_valid_findings(results, "duckduckgo")


async def test_arxiv_tool_live_search() -> None:
    results = await ArxivTool().search("retrieval augmented generation", max_results=3)
    if not results:
        pytest.skip("no results — Arxiv unreachable right now")
    assert len(results) <= 3
    _assert_valid_findings(results, "arxiv")
    assert "arxiv.org" in results[0]["url"]


async def test_wikipedia_tool_live_search() -> None:
    results = await WikipediaTool().search("retrieval augmented generation", max_results=3)
    if not results:
        pytest.skip("no results — Wikipedia unreachable right now")
    assert len(results) <= 3
    _assert_valid_findings(results, "wikipedia")
    assert "wikipedia.org" in results[0]["url"]
    # The snippet must have its <span class="searchmatch"> HTML markup
    # stripped (see wikipedia_search.py's _HTML_TAG substitution).
    assert "<span" not in results[0]["snippet"]
