from typing import ClassVar

from ai.loaders.base import BaseLoader, LoaderError


class TextLoader(BaseLoader):
    """Plain .txt files — decoded as UTF-8 with no further processing.
    `source` is the raw uploaded file bytes."""

    source_type: ClassVar[str] = "txt"

    async def load(self, source: bytes | str) -> str:
        if not isinstance(source, bytes):
            raise LoaderError("TextLoader expects raw file bytes")
        try:
            text = source.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise LoaderError(f"could not decode text file as UTF-8: {exc}") from exc

        if not text.strip():
            raise LoaderError("text file was empty")
        return text
