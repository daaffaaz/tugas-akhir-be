import numpy as np

import faiss

from apps.rag import config


def build_faiss_index(embeddings: list[list[float]]) -> faiss.Index:
    """Build FAISS IndexFlatIP from embedding vectors (normalized for cosine similarity)."""
    if not embeddings:
        raise ValueError("No embeddings provided")

    embeddings_np = np.array(embeddings, dtype=np.float32)
    norms = np.linalg.norm(embeddings_np, axis=1, keepdims=True)
    norms[norms == 0] = 1
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
    """Search FAISS index for top-k nearest neighbours. Returns [(idx, score), ...]."""
    if k is None:
        k = config.RAG_TOP_K
    if threshold is None:
        threshold = config.RAG_SIMILARITY_THRESHOLD

    query_np = np.array([query_vector], dtype=np.float32)
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

    results.sort(key=lambda x: x[1], reverse=True)
    return results
