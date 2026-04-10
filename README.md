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

python3 -m venv .venv
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

## How chunking works

Large documentation pages can't be embedded as a whole — embedding models have token limits, and embedding an entire page would bury the relevant detail in noise. Chunking solves this by splitting each page into smaller, overlapping pieces before embedding.

`ingest/chunk.py` uses a **sliding word-window** approach:

- Each cleaned page is split into chunks of **400 words** (configurable via `CHUNK_SIZE` in `config.py`)
- Adjacent chunks overlap by **50 words** (`CHUNK_OVERLAP`) so that sentences that fall on a boundary aren't split across two unrelated chunks
- Chunks shorter than **30 words** are discarded as they're too thin to be useful
- Each chunk is saved as a JSONL record with its source URL and service tag so retrieved chunks always carry attribution

At query time, the question is embedded using the same model, and the top-k most similar chunks are retrieved from ChromaDB. Those chunks — not full pages — are what gets sent to Claude, keeping the prompt focused and within token limits.

You can tune `CHUNK_SIZE`, `CHUNK_OVERLAP`, and `TOP_K` in `config.py` if retrieval quality feels off. Smaller chunks improve precision; larger chunks preserve more context per result.

## How embeddings work

Embeddings are the mechanism that makes semantic search possible. Instead of matching keywords, embeddings convert text into a list of numbers (a vector) that captures its *meaning*. Two pieces of text about the same concept will have similar vectors even if they use different words.

**During ingestion**, each chunk is passed through `all-MiniLM-L6-v2`, a lightweight embedding model that runs locally via `sentence-transformers`. The model outputs a 384-dimension vector for each chunk. That vector, along with the chunk text and its metadata (URL, service), is stored in ChromaDB.

**During a query**, the same model embeds your question into a vector using the exact same process. ChromaDB then computes the cosine similarity between your question vector and every stored chunk vector, returning the top-k closest matches.

Cosine similarity measures the angle between two vectors — a score of 1.0 means identical meaning, 0.0 means unrelated. The `--debug` flag on `query.py` prints the similarity score for each retrieved chunk, which is useful for diagnosing poor results.

Because the same model is used for both ingestion and querying, the vector space is consistent — the question and the chunks live in the same coordinate system, so comparison is meaningful.

The model weights are downloaded once on first run and cached locally by `sentence-transformers` in `~/.cache/huggingface/`. No data leaves your machine during embedding.

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
