
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_pages(
    extracted_pages: list[dict],
    chunk_size: int = 800,
    chunk_overlap: int = 160,
) -> list[Document]:
    """
    Split extracted PDF pages into overlapping chunks.

    Each chunk retains its source filename and original PDF page number.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative.")

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size.")

    if not extracted_pages:
        raise ValueError("No extracted pages were provided.")

    documents = []

    for item in extracted_pages:
        text = item.get("text", "").strip()
        metadata = item.get("metadata", {})

        if not text:
            continue

        if "page" not in metadata or "source" not in metadata:
            raise ValueError(
                "Each page must contain source and page metadata."
            )

        documents.append(
            Document(
                page_content=text,
                metadata=dict(metadata),
            )
        )

    if not documents:
        raise ValueError("No non-empty page text was provided.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
        add_start_index=True,
    )

    chunks = splitter.split_documents(documents)

    for chunk_index, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = chunk_index

    return chunks
