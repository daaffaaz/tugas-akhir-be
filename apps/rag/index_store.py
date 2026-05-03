import pickle
from pathlib import Path

import faiss
import numpy as np

from apps.rag import config as rag_config


def get_index_path() -> Path:
    """Return the FAISS index file path, searching from project root."""
    # Primary: config.FAISS_INDEX_FILE (data/rag_index/faiss_index.pkl)
    # Fallback: sibling media/rag_index/faiss_index.pkl (gitignored sibling directory)
    candidates = [
        rag_config.FAISS_INDEX_FILE,
        rag_config.BASE_DIR.parent / 'media' / 'rag_index' / 'faiss_index.pkl',
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"FAISS index not found. Run 'python manage.py build_faiss_index' first. "
        f"Searched: {candidates}"
    )


def load_faiss_index() -> tuple:
    """
    Load FAISS index and metadata from .pkl file.
    Returns (index, metadata_list) where metadata_list is list[dict].
    """
    path = get_index_path()
    with open(path, 'rb') as f:
        data = pickle.load(f)

    index = data['index']
    metadata = data['metadata']
    return index, metadata


def save_faiss_index(index, metadata: list[dict], path: Path | None = None):
    """Save FAISS index and metadata to .pkl file."""
    if path is None:
        path = rag_config.FAISS_INDEX_FILE

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'wb') as f:
        pickle.dump({'index': index, 'metadata': metadata}, f)


# ─── Module-level FAISS singleton ─────────────────────────────────────────────
# Loaded lazily on first access; survives warm Lambda/Cloud Run invocations.
_index: faiss.Index | None = None
_metadata: list[dict] | None = None


def get_faiss_index() -> faiss.Index:
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