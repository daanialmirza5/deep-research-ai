import asyncio
from io import BytesIO
from typing import ClassVar

import pypdf

from ai.loaders.base import BaseLoader, LoaderError


def _extract(content: bytes) -> str:
    try:
        reader = pypdf.PdfReader(BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # noqa: BLE001 - pypdf raises several distinct error types for malformed PDFs
        raise LoaderError(f"could not read PDF: {exc}") from exc
    return "\n\n".join(p for p in pages if p.strip())


class PdfLoader(BaseLoader):
    """Extracts text page-by-page via pypdf. `source` is the raw uploaded
    PDF bytes."""

    source_type: ClassVar[str] = "pdf"

    async def load(self, source: bytes | str) -> str:
        if not isinstance(source, bytes):
            raise LoaderError("PdfLoader expects raw file bytes")
        text = await asyncio.to_thread(_extract, source)
        if not text.strip():
            raise LoaderError("PDF contained no extractable text")
        return text
