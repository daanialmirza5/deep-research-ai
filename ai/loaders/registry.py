"""Maps a document's source_type (app.models.document.DocumentSourceType's
values, mirrored here as plain strings so ai/ stays independent of the
backend) to the BaseLoader that knows how to extract its text.
"""

from ai.loaders.base import BaseLoader
from ai.loaders.csv_loader import CsvLoader
from ai.loaders.docx_loader import DocxLoader
from ai.loaders.markdown_loader import MarkdownLoader
from ai.loaders.pdf_loader import PdfLoader
from ai.loaders.text_loader import TextLoader
from ai.loaders.url_loader import UrlLoader
from ai.loaders.youtube_loader import YoutubeLoader

_LOADERS: dict[str, BaseLoader] = {
    loader.source_type: loader
    for loader in (
        PdfLoader(),
        DocxLoader(),
        TextLoader(),
        MarkdownLoader(),
        CsvLoader(),
        UrlLoader(),
        YoutubeLoader(),
    )
}


def get_loader(source_type: str) -> BaseLoader:
    try:
        return _LOADERS[source_type]
    except KeyError:
        raise ValueError(f"no loader registered for source_type {source_type!r}") from None
