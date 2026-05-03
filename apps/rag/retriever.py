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
    Main retrieval pipeline.
    1. Embed the topic query.
    2. Search FAISS index.
    3. Return (list of course metadata dicts, top_similarity_score).
    """
    if top_k is None:
        top_k = config.RAG_TOP_K
    if threshold is None:
        threshold = config.RAG_SIMILARITY_THRESHOLD

    # Embed query
    query_vector = embedder.embed_text_cached(topic)

    # Load FAISS index (graceful error if missing)
    try:
        index = index_store.get_faiss_index()
    except FileNotFoundError:
        logger.warning("[retriever] FAISS index not found — returning empty results.")
        return [], 0.0

    # Search
    raw_results = vector_store.search_index(index, query_vector, k=top_k, threshold=threshold)

    # Load metadata
    all_metadata = index_store.get_metadata()

    # Map results to metadata
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


def retrieve_with_filter(
    topic: str,
    level: str | None = None,
    budget_max: float | None = None,
    top_k: int | None = None,
) -> list[dict]:
    """
    Retrieval with optional post-filter on metadata.
    Returns filtered list of course metadata dicts.
    """
    courses, _ = retrieve_courses(topic, top_k=top_k or 30)

    if level:
        courses = [c for c in courses if level.lower() in (c.get('level') or '').lower()]

    if budget_max is not None:
        courses = [
            c for c in courses
            if c.get('price') is None or c.get('price', 0) <= budget_max
        ]

    return courses


def retrieve_courses_for_replace(
    replaced_course_id: str,
    topic: str,
    user_profile: dict | None = None,
    additional_context: str | None = None,
    exclude_ids: list[str] | None = None,
    top_k: int = 20,
) -> list[dict]:
    """
    Find replacement candidates for a specific course.
    Searches FAISS for courses similar to 'topic', optionally boosted by
    the replaced course's text, excluding courses already in the path.
    Returns top_k candidate metadata dicts.
    """
    courses, top_score = retrieve_courses(topic, user_profile, top_k=top_k)

    # Exclude courses already in the learning path
    if exclude_ids:
        courses = [c for c in courses if c.get('course_id') not in exclude_ids]

    logger.info(
        f"[retriever] Replacement search: topic='{topic}', "
        f"replaced={replaced_course_id}, candidates={len(courses)}"
    )
    return courses, top_score