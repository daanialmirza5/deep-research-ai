import asyncio
from typing import ClassVar

from bs4 import BeautifulSoup
from markdown_it import MarkdownIt

from ai.loaders.base import BaseLoader, LoaderError

_md = MarkdownIt()


def _render_to_plain_text(raw: str) -> str:
    html = _md.render(raw)
    return BeautifulSoup(html, "html.parser").get_text(separator="\n").strip()


class MarkdownLoader(BaseLoader):
    """Renders Markdown to HTML (markdown-it-py) then strips tags, so
    heading/bold/link syntax doesn't pollute the embedded text — just the
    readable prose. `source` is the raw uploaded file bytes."""

    source_type: ClassVar[str] = "markdown"

    async def load(self, source: bytes | str) -> str:
        if not isinstance(source, bytes):
            raise LoaderError("MarkdownLoader expects raw file bytes")
        try:
            raw = source.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise LoaderError(f"could not decode markdown file as UTF-8: {exc}") from exc

        text = await asyncio.to_thread(_render_to_plain_text, raw)
        if not text:
            raise LoaderError("markdown file contained no extractable text")
        return text
