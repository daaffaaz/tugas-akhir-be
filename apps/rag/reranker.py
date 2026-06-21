"""
Cross-Encoder Reranker for RAG Pipeline.

Uses a lightweight cross-encoder model to rerank initial FAISS results
based on (query, course) relevance. Improves precision@K of top results
sent to the LLM generator.
"""
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Lazy import — only load the model when reranker is actually used.
_model = None
_tokenizer = None
_device = None
_model_loaded = False
_load_error: str | None = None


def _load_model():
    """Lazy-load the cross-encoder model. Falls back gracefully if unavailable."""
    global _model, _tokenizer, _device, _model_loaded, _load_error
    if _model_loaded:
        return

    try:
        from sentence_transformers import CrossEncoder  # type: ignore
        import torch  # type: ignore

        model_name = os.environ.get(
            "RERANKER_MODEL",
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
        )
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = CrossEncoder(model_name, device=_device)
        _model_loaded = True
        logger.info(f"[reranker] Loaded CrossEncoder '{model_name}' on device={_device}")
    except Exception as exc:  # noqa: BLE001
        _load_error = str(exc)
        _model_loaded = True
        logger.warning(f"[reranker] CrossEncoder unavailable, will use LLM fallback: {exc}")


def is_available() -> bool:
    """True if the cross-encoder model loaded successfully."""
    _load_model()
    return _model is not None


def rerank(
    query: str,
    courses: list[dict],
    top_k: int | None = None,
    return_scores: bool = False,
) -> list[dict]:
    """
    Rerank a list of course metadata dicts against the query.

    Each course dict is converted to text via `course_to_text()` and scored
    by the cross-encoder. Returns the courses sorted by reranker score desc.

    Args:
        query: User query string.
        courses: List of course metadata dicts (must contain at least
            course_id/title/description).
        top_k: If set, return only the top_k highest-scoring items.
        return_scores: If True, attach '_rerank_score' to each returned dict.

    Returns:
        Sorted list of course dicts (or original order if model unavailable).
    """
    _load_model()
    if not courses:
        return courses
    if _model is None:
        logger.debug("[reranker] Model unavailable, returning original order.")
        return courses

    from apps.rag.context_builder import course_to_text

    pairs = [(query, course_to_text(c)) for c in courses]
    try:
        scores = _model.predict(pairs, show_progress_bar=False)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[reranker] Inference failed: {exc}")
        return courses

    indexed = list(zip(courses, scores))
    indexed.sort(key=lambda x: float(x[1]), reverse=True)
    ranked = [c for c, _ in indexed]

    if top_k is not None and top_k > 0:
        ranked = ranked[:top_k]

    if return_scores:
        for c, s in indexed[: len(ranked)]:
            c["_rerank_score"] = float(s)

    logger.info(
        f"[reranker] query='{query[:60]}' in={len(courses)} out={len(ranked)} "
        f"top_score={indexed[0][1]:.3f}"
    )
    return ranked


def rerank_with_fallback(
    query: str,
    courses: list[dict],
    top_k: int | None = None,
    fallback_top_k: int = 5,
) -> list[dict]:
    """
    Rerank and return top results; if the model is unavailable, fall back
    to the original top_k (truncated).
    """
    if not is_available():
        return courses[: (top_k or fallback_top_k)]
    return rerank(query, courses, top_k=top_k, return_scores=True)
