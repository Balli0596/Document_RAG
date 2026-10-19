
import uuid
from pathlib import Path

import chromadb

from src.embeddings import embed_texts, embed_query


DEFAULT_DB_PATH = Path("chroma_db")
DEFAULT_COLLECTION = "pdf_chunks"


def get_collection(
    db_path: str | Path = DEFAULT_DB_PATH,
    collection_name: str = DEFAULT_COLLECTION,
):
    """Open or create a persistent ChromaDB collection."""

    client = chromadb.PersistentClient(path=str(db_path))

    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def index_chunks(
    chunks,
    collection,
    replace_existing: bool = True,
) -> int:
    """Embed and store chunks with their metadata."""

    if not chunks:
        raise ValueError("Cannot index an empty list of chunks.")

    if replace_existing and collection.count() > 0:
        collection.delete(
            ids=collection.get()["ids"]
        )

    texts = [chunk.page_content for chunk in chunks]

    if any(not text.strip() for text in texts):
        raise ValueError("Chunks must contain non-empty text.")

    embeddings = embed_texts(texts)

    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [dict(chunk.metadata) for chunk in chunks]

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return len(ids)


def retrieve_chunks(
    query: str,
    collection,
    top_k: int = 4,
    max_cosine_distance: float | None = 0.45,
) -> list[dict]:
    """
    Retrieve relevant chunks.

    Chroma cosine distance is approximately 1 - cosine similarity
    for nonzero vectors. Lower distances indicate closer matches.

    The distance threshold is a configurable starting point,
    not a universal measure of answer correctness.
    """

    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query must be a non-empty string.")

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    if max_cosine_distance is not None and not (
        0 <= max_cosine_distance <= 2
    ):
        raise ValueError("Cosine distance threshold must be between 0 and 2.")

    if collection.count() == 0:
        return []

    query_embedding = embed_query(query)

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    retrieved = []

    documents = result["documents"][0]
    metadatas = result["metadatas"][0]
    distances = result["distances"][0]

    for text, metadata, distance in zip(
        documents, metadatas, distances
    ):
        distance = float(distance)

        if (
            max_cosine_distance is not None
            and distance > max_cosine_distance
        ):
            continue

        retrieved.append(
            {
                "text": text,
                "metadata": metadata,
                "cosine_distance": distance,
                "cosine_similarity": 1.0 - distance,
            }
        )

    return retrieved
