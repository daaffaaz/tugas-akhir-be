import time
from typing import Any

import openai
from openai import OpenAI

from apps.rag import config

client = OpenAI(api_key=config.OPENAI_API_KEY)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Batch embed a list of texts using text-embedding-3-small.
    Handles rate limits with exponential backoff retry.
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
            except openai.RateLimitError as e:
                wait = (2 ** attempt) * 1.5
                print(f"[embedder] Rate limit, retrying in {wait:.1f}s... (attempt {attempt + 1})")
                time.sleep(wait)
            except Exception as e:
                print(f"[embedder] Error: {e}")
                # Append zero vector as fallback
                results.extend([[0.0] * 1536 for _ in batch])
                break

    return results


def embed_query(query: str) -> list[float]:
    """Embed a single query string."""
    return embed_texts([query])[0]


# Cache for repeated embeddings (in-process, cleared on cold start)
_embed_cache: dict[str, list[float]] = {}


def embed_text_cached(text: str) -> list[float]:
    """Embed with in-process deduplication cache."""
    key = text[:200]  # truncate key to avoid huge strings
    if key not in _embed_cache:
        _embed_cache[key] = embed_texts([text])[0]
    return _embed_cache[key]