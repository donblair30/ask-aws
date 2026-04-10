"""
Generate embeddings locally with sentence-transformers and upsert into ChromaDB.

The model (all-MiniLM-L6-v2) is downloaded once on first run and cached
by the sentence-transformers library in ~/.cache/huggingface/.

Usage:
    python -m store.embed               # embed all services
    python -m store.embed s3            # embed one service
"""

import json
import sys
from pathlib import Path

from sentence_transformers import SentenceTransformer

import config
from store.chroma import upsert, collection_size

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"Loading embedding model: {config.EMBED_MODEL}")
        _model = SentenceTransformer(config.EMBED_MODEL)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    return get_model().encode(texts, show_progress_bar=False).tolist()


def embed_service(service: str, batch_size: int = 64) -> int:
    """
    Read all JSONL chunk files for a service, embed in batches, upsert to Chroma.
    Returns number of chunks embedded.
    """
    chunk_dir = config.CHUNKS_DIR / service
    if not chunk_dir.exists():
        print(f"No chunks for {service}. Run chunk.py first.")
        return 0

    jsonl_files = sorted(chunk_dir.glob("*.jsonl"))
    total = 0

    batch_ids: list[str] = []
    batch_texts: list[str] = []
    batch_metas: list[dict] = []

    def _flush():
        nonlocal total
        if not batch_texts:
            return
        embeddings = embed_texts(batch_texts)
        upsert(
            ids=batch_ids,
            embeddings=embeddings,
            documents=batch_texts,
            metadatas=batch_metas,
        )
        total += len(batch_texts)
        batch_ids.clear()
        batch_texts.clear()
        batch_metas.clear()

    for jsonl_path in jsonl_files:
        with jsonl_path.open(encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)
                batch_ids.append(record["id"])
                batch_texts.append(record["text"])
                batch_metas.append({
                    "url":     record["url"],
                    "service": record["service"],
                })
                if len(batch_texts) >= batch_size:
                    _flush()
                    print(f"  embedded {total} chunks...", end="\r")

    _flush()
    print(f"{service}: {total} chunks embedded")
    return total


def embed_all(batch_size: int = 64) -> None:
    services = [d.name for d in config.CHUNKS_DIR.iterdir() if d.is_dir()]
    grand_total = 0
    for service in sorted(services):
        grand_total += embed_service(service, batch_size=batch_size)
    print(f"\nTotal: {grand_total} chunks | Collection size: {collection_size()}")


if __name__ == "__main__":
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else None
    if arg:
        embed_service(arg)
    else:
        embed_all()
