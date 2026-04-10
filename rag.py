"""
RAG pipeline: embed question → retrieve chunks → call Claude → return answer + sources.
"""

import anthropic

import config
from store.embed import embed_texts
from store.chroma import query as chroma_query

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not config.ANTHROPIC_API_KEY:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. "
                "Copy .env.example to .env and add your key."
            )
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


SYSTEM_PROMPT = """\
You are an expert AWS solutions architect helping developers understand AWS services.

Answer the question using ONLY the documentation excerpts provided. Be specific and practical.
- Include AWS CLI commands, SDK snippets, or policy JSON where relevant.
- Mention required IAM permissions when they matter.
- If the excerpts don't contain enough information to answer fully, say so.
- At the end, list the source URLs you drew from under a "Sources:" heading.
Do not invent information not present in the excerpts.\
"""


def _build_context(chunks: list[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        header = f"[{i}] {chunk['service'].upper()} — {chunk['url']}"
        parts.append(f"{header}\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


def answer(question: str, n_results: int = None) -> dict:
    """
    Run the full RAG pipeline for a question.

    Returns:
        {
            "answer":  str,          # Claude's response
            "sources": list[str],    # deduplicated source URLs
            "chunks":  list[dict],   # raw retrieved chunks (for debugging)
        }
    """
    n_results = n_results or config.TOP_K

    # 1. Embed the question locally
    [q_embedding] = embed_texts([question])

    # 2. Retrieve top-k chunks from ChromaDB
    chunks = chroma_query(q_embedding, n_results=n_results)

    if not chunks:
        return {
            "answer":  "No relevant documentation found in the index. "
                       "Make sure the ingestion pipeline has been run.",
            "sources": [],
            "chunks":  [],
        }

    # 3. Build the prompt
    context = _build_context(chunks)
    user_message = (
        f"Documentation excerpts:\n\n{context}\n\n"
        f"---\n\nQuestion: {question}"
    )

    # 4. Call Claude
    response = get_client().messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    answer_text = response.content[0].text

    # Deduplicate sources while preserving relevance order
    seen: set[str] = set()
    sources: list[str] = []
    for chunk in chunks:
        url = chunk["url"]
        if url not in seen:
            seen.add(url)
            sources.append(url)

    return {"answer": answer_text, "sources": sources, "chunks": chunks}
