import time

import openai
from openai import OpenAI

from apps.rag import config

client = OpenAI(api_key=config.OPENAI_API_KEY)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Batch embed texts using text-embedding-3-small.
    Handles rate limits with exponential backoff.
    """
    results = []
    batch_size = config.EMBEDDING_BATCH_SIZE

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        for attempt in range(4):
            try:
                response = client.embeddings.create(
                    model=config.EMBEDDING_MODEL,
                    input=batch,
                )
                for item in response.data:
                    results.append(item.embedding)
                break
            except openai.RateLimitError:
                wait = (2 ** attempt) * 1.5
                print(f"[embedder] Rate limit, retrying in {wait:.1f}s...")
                time.sleep(wait)
            except Exception as e:
                print(f"[embedder] Error: {e}")
                results.extend([[0.0] * 1536 for _ in batch])
                break

    return results


def embed_query(query: str) -> list[float]:
    """Embed a single query string."""
    return embed_texts([query])[0]


# In-process cache
_embed_cache: dict[str, list[float]] = {}


def embed_text_cached(text: str) -> list[float]:
    """Embed with deduplication cache."""
    key = text[:200]
    if key not in _embed_cache:
        _embed_cache[key] = embed_texts([text])[0]
    return _embed_cache[key]
