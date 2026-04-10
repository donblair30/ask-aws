"""
Split cleaned text files into overlapping word-count chunks and write JSONL
to data/chunks/{service}/.

Each chunk record:
    {
        "id":      "<service>_<url_hash>_<chunk_index>",
        "text":    "...",
        "url":     "https://docs.aws.amazon.com/...",
        "service": "s3" | "ec2" | "iam"
    }

Strategy: slide a fixed-size window (in words) with overlap across the text.
Simple and robust — avoids brittle heading-detection heuristics.

Usage:
    python -m ingest.chunk              # chunk all services
    python -m ingest.chunk s3           # chunk one service
"""

import hashlib
import json
import sys
from pathlib import Path

import config
from ingest.corpus import SERVICE_SITEMAPS, discover_urls
from ingest.fetch import url_to_filename


def _sliding_chunks(text: str, size: int, overlap: int) -> list[str]:
    """Split text into overlapping word-window chunks."""
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += size - overlap
    return chunks


def chunk_text(text: str, url: str, service: str) -> list[dict]:
    """
    Produce chunk records for one document.
    Chunks shorter than MIN_CHUNK_WORDS are discarded.
    """
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    raw_chunks = _sliding_chunks(text, config.CHUNK_SIZE, config.CHUNK_OVERLAP)

    records = []
    for i, chunk in enumerate(raw_chunks):
        if len(chunk.split()) < config.MIN_CHUNK_WORDS:
            continue
        records.append({
            "id":      f"{service}_{url_hash}_{i}",
            "text":    chunk,
            "url":     url,
            "service": service,
        })
    return records


def chunk_service(service: str) -> int:
    """
    Chunk all cleaned text files for a service.
    Writes one JSONL file per source page to data/chunks/{service}/.
    Returns total chunk count.
    """
    raw_dir = config.RAW_DIR / service
    out_dir = config.CHUNKS_DIR / service
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build filename → URL lookup from corpus so each chunk carries its source URL
    entries = discover_urls(service)
    filename_to_url = {url_to_filename(e["url"]): e["url"] for e in entries}

    total = 0
    txt_files = sorted(raw_dir.glob("*.txt"))

    for txt_path in txt_files:
        # Derive the corresponding HTML filename to look up the URL
        html_name = txt_path.stem + ".html"
        url = filename_to_url.get(html_name)
        if not url:
            continue  # file not in corpus (shouldn't happen)

        text = txt_path.read_text(encoding="utf-8").strip()
        if not text:
            continue

        records = chunk_text(text, url, service)
        if not records:
            continue

        out_path = out_dir / (txt_path.stem + ".jsonl")
        with out_path.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")

        total += len(records)

    print(f"{service}: {total} chunks from {len(txt_files)} files")
    return total


def chunk_all() -> None:
    services = [d.name for d in config.RAW_DIR.iterdir() if d.is_dir()]
    grand_total = 0
    for service in sorted(services):
        grand_total += chunk_service(service)
    print(f"\nTotal: {grand_total} chunks")


if __name__ == "__main__":
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else None
    if arg:
        chunk_service(arg)
    else:
        chunk_all()
