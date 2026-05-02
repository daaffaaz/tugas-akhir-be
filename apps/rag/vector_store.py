import numpy as np

import faiss

from apps.rag import config, index_store


def build_faiss_index(embeddings: list[list[float]]) -> faiss.Index:
    """
    Build a FAISS IndexFlatIP (Inner Product) index from a list of embedding vectors.
    Uses Inner Product for cosine similarity (embeddings must be normalized first).
    """
    if not embeddings:
        raise ValueError("No embeddings provided to build index")

    embeddings_np = np.array(embeddings, dtype=np.float32)

    # Normalize for cosine similarity
    norms = np.linalg.norm(embeddings_np, axis=1, keepdims=True)
    norms[norms == 0] = 1  # avoid divide by zero
    embeddings_np = embeddings_np / norms

    dim = embeddings_np.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings_np)

    return index


def search_index(
    index: faiss.Index,
    query_vector: list[float],
    k: int | None = None,
    threshold: float | None = None,
) -> list[tuple[int, float]]:
    """
    Search FAISS index for top-k nearest neighbours.
    Returns list of (index_position, similarity_score) sorted by score descending.
    """
    if k is None:
        k = config.RAG_TOP_K
    if threshold is None:
        threshold = config.RAG_SIMILARITY_THRESHOLD

    query_np = np.array([query_vector], dtype=np.float32)
    # Normalize query for cosine similarity
    norms = np.linalg.norm(query_np, axis=1, keepdims=True)
    norms[norms == 0] = 1
    query_np = query_np / norms

    distances, indices = index.search(query_np, k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0:
            continue
        if threshold is not None and dist < threshold:
            continue
        results.append((int(idx), float(dist)))

    # Sort by score descending
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def search_from_chunks(
    query_vector: list[float],
    chunks: list[dict],
    k: int | None = None,
    threshold: float | None = None,
) -> list[tuple[dict, float]]:
    """
    Build a temporary FAISS index from a list of chunk metadata dicts
    and search it. Used for on-demand search without a pre-built index.
    Returns list of (chunk_metadata, similarity_score).
    """
    if not chunks:
        return []

    from apps.rag import embedder

    texts = [c['text'] for c in chunks]
    embs = embedder.embed_texts(texts)
    index = build_faiss_index(embs)

    raw_results = search_index(index, query_vector, k=k, threshold=threshold)
    return [(chunks[idx], score) for idx, score in raw_results]