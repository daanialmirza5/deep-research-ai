import asyncio
from io import BytesIO
from typing import ClassVar

import docx

from ai.loaders.base import BaseLoader, LoaderError


def _extract(content: bytes) -> str:
    try:
        document = docx.Document(BytesIO(content))
        paragraphs = [p.text for p in document.paragraphs]
    except Exception as exc:  # noqa: BLE001 - python-docx raises several distinct error types
        raise LoaderError(f"could not read DOCX: {exc}") from exc
    return "\n\n".join(p for p in paragraphs if p.strip())


class DocxLoader(BaseLoader):
    """Extracts paragraph text via python-docx. `source` is the raw
    uploaded DOCX bytes."""

    source_type: ClassVar[str] = "docx"

    async def load(self, source: bytes | str) -> str:
        if not isinstance(source, bytes):
            raise LoaderError("DocxLoader expects raw file bytes")
        text = await asyncio.to_thread(_extract, source)
        if not text.strip():
            raise LoaderError("DOCX contained no extractable text")
        return text
