import pytest

from ai.chunking import chunk_text


def test_empty_text_produces_no_chunks() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_short_text_is_a_single_chunk() -> None:
    text = "A short paragraph that easily fits in one chunk."
    assert chunk_text(text, chunk_size=1000, chunk_overlap=200) == [text]


def test_paragraphs_are_grouped_until_chunk_size_is_exceeded() -> None:
    paragraphs = ["a" * 40, "b" * 40, "c" * 40]
    text = "\n\n".join(paragraphs)

    chunks = chunk_text(text, chunk_size=90, chunk_overlap=10)

    # First two paragraphs (40 + 2 + 40 = 82 chars) fit under 90; the third
    # doesn't fit alongside them and starts a new chunk.
    assert len(chunks) == 2
    assert "a" * 40 in chunks[0]
    assert "b" * 40 in chunks[0]
    assert "c" * 40 in chunks[1]


def test_consecutive_chunks_overlap() -> None:
    paragraphs = ["a" * 40, "b" * 40, "c" * 40]
    text = "\n\n".join(paragraphs)

    chunks = chunk_text(text, chunk_size=90, chunk_overlap=10)

    assert len(chunks) == 2
    # The tail of chunk 0 reappears at the head of chunk 1.
    assert chunks[0][-10:] in chunks[1]


def test_a_single_paragraph_longer_than_chunk_size_is_hard_cut() -> None:
    text = "x" * 250

    chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)

    assert len(chunks) == 3
    assert all(len(c) <= 100 for c in chunks)
    # No content is lost across the hard cuts.
    assert "".join(chunks).replace("x", "") == ""
    assert sum(c.count("x") for c in chunks) >= 250


def test_chunk_overlap_must_be_smaller_than_chunk_size() -> None:
    with pytest.raises(ValueError, match="chunk_overlap must be smaller"):
        chunk_text("hello", chunk_size=100, chunk_overlap=100)
