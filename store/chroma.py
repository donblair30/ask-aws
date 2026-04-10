"""
ChromaDB setup and query helpers.

The collection uses cosine similarity. Embeddings are stored alongside
document text and metadata (url, service) so retrieval returns everything
needed to build the LLM prompt.
"""

import chromadb
from chromadb.config import Settings

import config

_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None

COLLECTION_NAME = "aws_docs"


def get_collection() -> chromadb.Collection:
    global _client, _collection
    if _collection is None:
        config.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(config.CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def upsert(ids: list[str], embeddings: list[list[float]],
           documents: list[str], metadatas: list[dict]) -> None:
    get_collection().upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )


def query(embedding: list[float], n_results: int = None,
          service: str | None = None) -> list[dict]:
    """
    Retrieve the top-k most similar chunks.

    Returns a list of dicts:
        {"text": ..., "url": ..., "service": ..., "score": float 0-1}
    where score=1 is a perfect cosine match.
    """
    n_results = n_results or config.TOP_K
    collection = get_collection()

    where = {"service": service} if service else None

    results = collection.query(
        query_embeddings=[embedding],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text":    doc,
            "url":     meta["url"],
            "service": meta["service"],
            "score":   round(1.0 - dist, 4),  # cosine distance → similarity
        })

    return chunks


def collection_size() -> int:
    return get_collection().count()
