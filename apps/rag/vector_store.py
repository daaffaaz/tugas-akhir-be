import numpy as np

from apps.rag import config


def build_faiss_index(embeddings: list[list[float]]) -> np.ndarray:
    """
    Build a normalized embeddings matrix for cosine-similarity search.

    Returns a (n_vectors, dim) float32 numpy array with each row L2-normalized.
    Despite the legacy name, this no longer uses FAISS — pure NumPy is used to
    avoid SIGILL crashes on serverless runtimes whose CPUs lack the AVX2/AVX512
    instructions baked into faiss-cpu wheels.
    """
    if not embeddings:
        raise ValueError("No embeddings provided to build index")

    matrix = np.asarray(embeddings, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return matrix / norms


def search_index(
    index: np.ndarray,
    query_vector: list[float],
    k: int | None = None,
    threshold: float | None = None,
) -> list[tuple[int, float]]:
    """
    Search the embeddings matrix for top-k nearest neighbours by cosine similarity.
    Returns list of (row_index, similarity_score) sorted by score descending.
    """
    if k is None:
        k = config.RAG_TOP_K
    if threshold is None:
        threshold = config.RAG_SIMILARITY_THRESHOLD

    query = np.asarray(query_vector, dtype=np.float32)
    norm = np.linalg.norm(query)
    if norm == 0:
        return []
    query = query / norm

    scores = index @ query  # cosine similarity since both sides are L2-normalized

    k = min(k, scores.shape[0])
    # argpartition gives top-k unsorted, then we sort just those k.
    top_idx = np.argpartition(-scores, k - 1)[:k]
    top_idx = top_idx[np.argsort(-scores[top_idx])]

    results: list[tuple[int, float]] = []
    for idx in top_idx:
        score = float(scores[idx])
        if threshold is not None and score < threshold:
            continue
        results.append((int(idx), score))

    return results


def search_from_chunks(
    query_vector: list[float],
    chunks: list[dict],
    k: int | None = None,
    threshold: float | None = None,
) -> list[tuple[dict, float]]:
    """
    Build a temporary embeddings matrix from a list of chunk metadata dicts
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
