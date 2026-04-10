# ask-aws

A local RAG (Retrieval-Augmented Generation) pipeline that lets developers ask natural-language questions about AWS documentation and get accurate, sourced answers — without leaving the terminal.

Documentation is fetched directly from `docs.aws.amazon.com`, cleaned, chunked, and stored in a local vector database. Questions are answered by retrieving the most relevant chunks and passing them to Claude.

## What it does

1. **Ingests** AWS documentation from official sources (EC2, S3, IAM to start)
2. **Embeds** the content locally using `sentence-transformers`
3. **Stores** embeddings in a local ChromaDB database
4. **Answers** natural-language questions by retrieving relevant chunks and sending them to Claude via the Anthropic API

Everything except the final LLM call runs entirely on your machine.

## Tech stack

| Layer | Tool |
|---|---|
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`, runs locally) |
| Vector store | ChromaDB (local, persistent) |
| LLM | Claude (`claude-sonnet-4-6`) via Anthropic API |
| HTML fetching | `httpx` |
| HTML parsing | `beautifulsoup4` + `lxml` |
| Doc discovery | AWS sitemap XML |

## Installation

**Requirements:** Python 3.11+

```bash
git clone <your-repo-url>
cd ask-aws

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

## Configuration

You need an Anthropic API key for the answer-generation step.

```bash
cp .env.example .env
```

Open `.env` and add your key:

```
ANTHROPIC_API_KEY=your-key-here
```

> **Note:** `.env` is listed in `.gitignore` and will never be committed. Do not share it or check it in.

You can adjust chunking, retrieval, and model settings in `config.py`.

## Running the pipeline

The ingestion pipeline only needs to be run once (or when you want to refresh the docs). Raw HTML is cached locally so re-runs skip already-fetched pages.

### Option A — Make targets

```bash
# Ingest one service (recommended to start)
make ingest-s3

# Ingest all three services
make ingest

# Run a test query
make query
```

### Option B — Step by step

```bash
# 1. Discover URLs from AWS sitemaps
python -m ingest.corpus

# 2. Fetch and cache raw HTML
python -m ingest.fetch s3       # or ec2, iam, or omit for all

# 3. Strip boilerplate, extract plain text
python -m ingest.clean s3

# 4. Split into chunks
python -m ingest.chunk s3

# 5. Embed and store in ChromaDB
python -m store.embed s3
```

## Querying

```bash
python query.py "How do I control access to S3 buckets?"
python query.py "What IAM permissions does an ECS task execution role need?"
python query.py "How do EC2 placement groups affect network performance?"
```

### Options

```
--service s3|ec2|iam    Restrict retrieval to one service
--top-k N               Number of chunks to retrieve (default: 5)
--debug                 Print retrieved chunks and similarity scores
```

```bash
python query.py --service s3 --top-k 8 --debug "How does S3 versioning work?"
```

## Project structure

```
ask-aws/
├── ingest/
│   ├── corpus.py       # URL discovery via AWS sitemaps
│   ├── fetch.py        # HTML download + local cache
│   ├── clean.py        # Boilerplate removal → plain text
│   └── chunk.py        # Sliding-window chunking → JSONL
├── store/
│   ├── embed.py        # Embedding generation + ChromaDB upsert
│   └── chroma.py       # ChromaDB client + query helpers
├── rag.py              # Retrieve → prompt → Claude
├── query.py            # CLI entrypoint
├── config.py           # All tunable settings
├── requirements.txt
└── .env.example
```

Fetched HTML, chunks, and the vector database are stored under `data/` which is gitignored.
