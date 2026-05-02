import pickle
from pathlib import Path

import faiss
import numpy as np

from apps.rag import config


def get_index_path() -> Path:
    """Return the FAISS index file path."""
    base = Path(__file__).resolve().parent.parent.parent.parent
    candidates = [
        base / 'data' / 'rag_index' / 'faiss_index.pkl',
        base / 'media' / 'rag_index' / 'faiss_index.pkl',
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"FAISS index not found. Run 'python manage.py build_faiss_index' first. "
        f"Searched: {candidates}"
    )


def load_faiss_index() -> tuple:
    """Load FAISS index and metadata from .pkl file. Returns (index, metadata_list)."""
    path = get_index_path()
    with open(path, 'rb') as f:
        data = pickle.load(f)
    return data['index'], data['metadata']


def save_faiss_index(index, metadata: list[dict], path: Path | None = None):
    """Save FAISS index and metadata to .pkl file."""
    if path is None:
        path = config.FAISS_INDEX_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'wb') as f:
        pickle.dump({'index': index, 'metadata': metadata}, f)


# Module-level singleton
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
    """Force-reload the index from disk."""
    global _index, _metadata
    _index, _metadata = load_faiss_index()
