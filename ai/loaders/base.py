from abc import ABC, abstractmethod
from typing import ClassVar


class BaseLoader(ABC):
    """Extracts plain text from one document source type, keyed by
    `source_type` in the loader registry (ai/loaders/registry.py).

    File-based loaders (PDF/DOCX/TXT/CSV/Markdown) take the raw uploaded
    bytes; remote loaders (URL/YouTube) take a source string (URL) instead —
    each concrete loader documents which it expects.
    """

    source_type: ClassVar[str]

    @abstractmethod
    async def load(self, source: bytes | str) -> str:
        """Returns the extracted plain text. Raises LoaderError on failure
        (unreadable file, unreachable URL, no transcript available, etc.) —
        unlike ai/tools/base.py's BaseTool, a loader failure is the caller's
        one input, not one of several search results to shrug off, so it's
        surfaced rather than swallowed into an empty string."""


class LoaderError(Exception):
    """Raised when a loader cannot extract any text from its source."""
