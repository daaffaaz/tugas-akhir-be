import logging
import pickle
from pathlib import Path

import numpy as np

from apps.rag import config as rag_config

logger = logging.getLogger(__name__)


def get_index_path() -> Path:
    """Return the index file path, searching from project root."""
    candidates = [
        rag_config.FAISS_INDEX_FILE,                      # data/rag_index/faiss_index.pkl
        rag_config.BASE_DIR / 'data' / 'rag_index' / 'faiss_index.pkl',
        rag_config.BASE_DIR / 'media' / 'rag_index' / 'faiss_index.pkl',
        rag_config.BASE_DIR.parent / 'media' / 'rag_index' / 'faiss_index.pkl',
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"Index not found. Run 'python manage.py build_faiss_index' first. "
        f"Searched: {[str(p) for p in candidates]}"
    )


def load_faiss_index() -> tuple[np.ndarray, list[dict]]:
    """
    Load embeddings matrix and metadata from .pkl file.
    Returns (embeddings_matrix, metadata_list).

    Raises FileNotFoundError when the file is missing OR is in the legacy
    FAISS-object format (which would require the faiss package to unpickle).
    Callers already treat FileNotFoundError as "rebuild needed".
    """
    path = get_index_path()
    try:
        with open(path, 'rb') as f:
            data = pickle.load(f)
    except (ModuleNotFoundError, ImportError) as e:
        logger.warning(
            "[index_store] Index pickle requires a missing module (likely the "
            "legacy faiss-based format): %s. Rebuild the index.", e,
        )
        raise FileNotFoundError(f"Legacy index format at {path}; rebuild required.") from e

    if 'embeddings' in data:
        embeddings = np.asarray(data['embeddings'], dtype=np.float32)
        return embeddings, data['metadata']

    logger.warning(
        "[index_store] Index at %s is in the legacy FAISS-object format "
        "(missing 'embeddings' key). Rebuild via the build_faiss_index command.",
        path,
    )
    raise FileNotFoundError(f"Legacy index format at {path}; rebuild required.")


def save_faiss_index(index: np.ndarray, metadata: list[dict], path: Path | None = None):
    """Save embeddings matrix and metadata to .pkl file."""
    if path is None:
        path = rag_config.FAISS_INDEX_FILE

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'embeddings': np.asarray(index, dtype=np.float32),
        'metadata': metadata,
    }
    with open(path, 'wb') as f:
        pickle.dump(payload, f)


# ─── Module-level singleton ───────────────────────────────────────────────────
# Loaded lazily on first access; survives warm Lambda/Cloud Run invocations.
_index: np.ndarray | None = None
_metadata: list[dict] | None = None


def get_faiss_index() -> np.ndarray:
    global _index
    if _index is None:
        _index, _ = load_faiss_index()
    return _index


def get_metadata() -> list[dict]:
    global _metadata
    if _metadata is None:
        _, _metadata = load_faiss_index()
    return _metadata


def reload_index():
    """Force-reload the index from disk (useful after rebuild)."""
    global _index, _metadata
    _index, _metadata = load_faiss_index()
