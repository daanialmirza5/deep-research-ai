"""Splits raw document text into overlapping chunks for embedding.

A small, dependency-free splitter — not LangChain's `RecursiveCharacterTextSplitter`
(docs/tech-stack.md scopes LangChain's loaders/splitters to Phase 10's
format-aware document loaders: page boundaries for PDFs, heading-aware splits
for Markdown, etc.). This one only needs to turn a plain string into
reasonably-sized, context-preserving chunks so Phase 9's vector store has
real chunks to embed and search — Phase 10 can layer smarter, format-specific
splitting on top without this module's callers changing.
"""

_PARAGRAPH_BREAK = "\n\n"


def chunk_text(text: str, *, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    """Splits on paragraph boundaries where possible, falling back to a hard
    character cut for any single paragraph longer than chunk_size. Each chunk
    after the first repeats the last `chunk_overlap` characters of its
    predecessor so a fact split across a chunk boundary still appears whole
    in at least one chunk.
    """
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    paragraphs = [p.strip() for p in text.split(_PARAGRAPH_BREAK) if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""

    def _flush_overflowing(value: str) -> str:
        """Hard-cuts value down to under chunk_size, appending full chunks to
        `chunks` as it goes, and returns whatever remainder is left."""
        while len(value) > chunk_size:
            chunks.append(value[:chunk_size])
            value = value[chunk_size - chunk_overlap :]
        return value

    for paragraph in paragraphs:
        candidate = f"{current}{_PARAGRAPH_BREAK}{paragraph}" if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = current[-chunk_overlap:] + _PARAGRAPH_BREAK + paragraph
        else:
            current = paragraph
        current = _flush_overflowing(current)

    if current:
        chunks.append(current)

    return chunks
