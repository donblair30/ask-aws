# ask-aws

## Enterprise Knowledge Assistant (RAG) for AWS Documentation

Retrieval-Augmented Generation (RAG) application built on AWS documentation to simulate an enterprise knowledge assistant.

Answers technical questions by retrieving relevant documentation and generating responses with cited sources.

Focused on improving answer accuracy, reducing hallucinations, and providing source-grounded responses.

Designed to mirror internal enterprise knowledge systems (engineering docs, support knowledge bases, and internal wikis).

### Why This Matters

Reflects common enterprise challenges:
- Knowledge is fragmented across large documentation sets  
- Engineers spend significant time searching for answers  
- Responses must be accurate, traceable, and trustworthy  

## What it does

1. **Ingests** AWS documentation from official sources (EC2, S3, IAM to start)
2. **Embeds** the content locally using `sentence-transformers`
3. **Stores** embeddings in a local ChromaDB database
4. **Answers** natural-language questions by retrieving relevant chunks and sending them to Claude via the Anthropic API for grounded response generation

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

**Requirements:** Python 3.11 (3.12+ not recommended due to torch compatibility constraints)

```bash
git clone <your-repo-url>
cd ask-aws

python3.11 -m venv .venv
source .venv/bin/activate

pip3 install -r requirements.txt
```

> **Note:** If `python3.11` is not found, install it via Homebrew: `brew install python@3.11`. On Apple Silicon Macs, ensure you are using a native ARM64 Python for best performance.

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
python3 -m ingest.corpus

# 2. Fetch and cache raw HTML
python3 -m ingest.fetch s3       # or ec2, iam, or omit for all

# 3. Strip boilerplate, extract plain text
python3 -m ingest.clean s3

# 4. Split into chunks
python3 -m ingest.chunk s3

# 5. Embed and store in ChromaDB
python3 -m store.embed s3
```

## Querying

```bash
python3 query.py "How do I control access to S3 buckets?"
python3 query.py "What IAM permissions does an ECS task execution role need?"
python3 query.py "How do EC2 placement groups affect network performance?"
```

### Options

```
--service s3|ec2|iam    Restrict retrieval to one service
--top-k N               Number of chunks to retrieve (default: 5)
--debug                 Print retrieved chunks and similarity scores
```

```bash
python3 query.py --service s3 --top-k 8 --debug "How does S3 versioning work?"
```

## How the app works — end to end

The app has two distinct phases: **ingestion** (run once to build the knowledge base) and **querying** (run any time you have a question).

### Ingestion phase

```
AWS sitemaps → filtered URL list → raw HTML → clean text → chunks → embeddings → ChromaDB
```

1. **Discover** — `corpus.py` fetches the sitemap XML for each service and filters out API reference and CLI reference URLs, leaving only User Guide pages
2. **Fetch** — `fetch.py` downloads each page as raw HTML and caches it to `data/raw/{service}/`. Already-cached pages are skipped on re-runs
3. **Clean** — `clean.py` strips navigation, headers, footers, and other boilerplate using BeautifulSoup, leaving only the main content as plain text
4. **Chunk** — `chunk.py` splits each page into overlapping 400-word windows and saves them as JSONL records to `data/chunks/{service}/`
5. **Embed** — `store/embed.py` passes each chunk through the local embedding model and upserts the resulting vectors into ChromaDB

### Query phase

```
Your question → embedding → ChromaDB similarity search → top-k chunks → Claude → answer + sources
```

1. **Embed the question** — your question is converted to a vector using the same local model used during ingestion
2. **Retrieve** — ChromaDB finds the top-k chunks whose vectors are closest to the question vector
3. **Generate** — the retrieved chunks are assembled into a prompt and sent to Claude, which synthesises an answer grounded in the actual documentation
4. **Return** — the answer and source URLs are printed to the terminal
5. **Grounding** — responses are constrained to retrieved content to reduce hallucination risk

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

## Next Steps

- Improve retrieval quality (optimize chunking strategy, introduce re-ranking)
- Add evaluation framework (precision/recall, answer grounding, hallucination checks)
- Expand to multi-document datasets (simulate enterprise knowledge fragmentation)
- Introduce query understanding (query rewriting or multi-step retrieval)

