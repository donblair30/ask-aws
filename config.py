"""Central configuration for ask-aws."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Anthropic
ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL: str = "claude-sonnet-4-6"

# Paths
DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
CHUNKS_DIR = DATA_DIR / "chunks"
CHROMA_DIR = DATA_DIR / "chroma"

# Embedding model (runs locally via sentence-transformers)
EMBED_MODEL: str = "all-MiniLM-L6-v2"

# Chunking
CHUNK_SIZE: int = 350    # target words per chunk
CHUNK_OVERLAP: int = 40  # word overlap between adjacent chunks
MIN_CHUNK_WORDS: int = 20  # discard chunks shorter than this

# Retrieval
TOP_K: int = 5  # number of chunks to retrieve per query

# HTTP fetching
FETCH_DELAY_SECONDS: float = 0.5   # polite delay between requests
FETCH_TIMEOUT_SECONDS: int = 20
FETCH_HEADERS = {
    "User-Agent": "ask-aws/0.1 (local RAG; educational use)",
    "Accept": "text/html,application/xhtml+xml",
}
