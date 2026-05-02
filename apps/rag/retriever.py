import logging

from apps.rag import config, embedder, index_store, vector_store

logger = logging.getLogger(__name__)


def retrieve_courses(
    topic: str,
    user_profile: dict | None = None,
    top_k: int | None = None,
    threshold: float | None = None,
) -> tuple[list[dict], float]:
    """
    Main retrieval pipeline:
    1. Embed the topic query.
    2. Search FAISS index.
    3. Return (list of course metadata dicts, top_similarity_score).
    """
    if top_k is None:
        top_k = config.RAG_TOP_K
    if threshold is None:
        threshold = config.RAG_SIMILARITY_THRESHOLD

    query_vector = embedder.embed_text_cached(topic)
    index = index_store.get_faiss_index()
    raw_results = vector_store.search_index(index, query_vector, k=top_k, threshold=threshold)
    all_metadata = index_store.get_metadata()

    courses = []
    top_score = 0.0
    for idx, score in raw_results:
        if idx < len(all_metadata):
            meta = all_metadata[idx].copy()
            meta['_score'] = score
            courses.append(meta)
            if score > top_score:
                top_score = score

    logger.info(f"[retriever] Retrieved {len(courses)} courses for topic='{topic}', top_score={top_score:.3f}")
    return courses, top_score
