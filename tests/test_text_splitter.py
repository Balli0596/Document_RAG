
import pytest

from src.text_splitter import split_pages


def sample_pages():
    return [
        {
            "text": (
                "Machine learning uses data to learn patterns. "
                * 100
            ),
            "metadata": {
                "source": "sample.pdf",
                "page": 1,
            },
        },
        {
            "text": "Deep learning uses neural networks.",
            "metadata": {
                "source": "sample.pdf",
                "page": 2,
            },
        },
    ]


def test_chunks_respect_size_limit():
    chunks = split_pages(
        sample_pages(),
        chunk_size=200,
        chunk_overlap=40,
    )

    assert chunks
    assert all(len(chunk.page_content) <= 200 for chunk in chunks)


def test_metadata_is_preserved():
    chunks = split_pages(
        sample_pages(),
        chunk_size=200,
        chunk_overlap=40,
    )

    assert all(chunk.metadata["source"] == "sample.pdf" for chunk in chunks)
    assert {chunk.metadata["page"] for chunk in chunks} == {1, 2}


def test_chunk_indexes_are_unique():
    chunks = split_pages(sample_pages(), chunk_size=200, chunk_overlap=40)

    indexes = [chunk.metadata["chunk_index"] for chunk in chunks]

    assert indexes == list(range(len(chunks)))


def test_empty_input_raises_error():
    with pytest.raises(ValueError, match="No extracted pages"):
        split_pages([])


def test_invalid_overlap_raises_error():
    with pytest.raises(ValueError, match="smaller than chunk_size"):
        split_pages(sample_pages(), chunk_size=100, chunk_overlap=100)
