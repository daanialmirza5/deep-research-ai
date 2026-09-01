import asyncio
from typing import ClassVar

import httpx
from bs4 import BeautifulSoup

from ai.loaders.base import BaseLoader, LoaderError

# A descriptive User-Agent avoids the same class of block
# ai/tools/wikipedia_search.py hit without one (see that module's comment).
_USER_AGENT = "DeepResearchAI/0.1 (educational research project; no contact URL configured)"


def _strip_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    # get_text() preserves whitespace-only lines from empty/nested tags —
    # collapse those rather than embedding a page full of blank lines.
    lines = [line.strip() for line in soup.get_text(separator="\n").splitlines()]
    return "\n".join(line for line in lines if line)


class UrlLoader(BaseLoader):
    """Fetches a web page and extracts its visible text (script/style
    stripped). `source` is the page URL."""

    source_type: ClassVar[str] = "url"

    async def load(self, source: bytes | str) -> str:
        if not isinstance(source, str):
            raise LoaderError("UrlLoader expects a URL string")
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": _USER_AGENT}, timeout=15.0, follow_redirects=True
            ) as client:
                response = await client.get(source)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LoaderError(f"could not fetch {source}: {exc}") from exc

        text = await asyncio.to_thread(_strip_to_text, response.text)
        if not text:
            raise LoaderError(f"no extractable text at {source}")
        return text
