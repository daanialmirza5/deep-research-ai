import asyncio
import csv
import io
from typing import ClassVar

from ai.loaders.base import BaseLoader, LoaderError


def _extract(content: bytes) -> str:
    try:
        text_io = io.StringIO(content.decode("utf-8"))
        reader = csv.DictReader(text_io)
        lines = [", ".join(f"{key}: {value}" for key, value in row.items()) for row in reader]
    except (UnicodeDecodeError, csv.Error) as exc:
        raise LoaderError(f"could not read CSV: {exc}") from exc
    return "\n".join(lines)


class CsvLoader(BaseLoader):
    """Each row becomes one line of `column: value` pairs, using the header
    row as column names — turns tabular data into something an embedding
    model can meaningfully compare against prose queries. `source` is the
    raw uploaded file bytes."""

    source_type: ClassVar[str] = "csv"

    async def load(self, source: bytes | str) -> str:
        if not isinstance(source, bytes):
            raise LoaderError("CsvLoader expects raw file bytes")
        text = await asyncio.to_thread(_extract, source)
        if not text.strip():
            raise LoaderError("CSV contained no rows")
        return text
