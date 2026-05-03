from pathlib import Path

from decouple import config

# --- Retrieval Config ---
RAG_TOP_K: int = config('RAG_TOP_K', default=15, cast=int)
RAG_MAX_CONTEXT_COURSES: int = config('RAG_MAX_CONTEXT_COURSES', default=12, cast=int)
RAG_SIMILARITY_THRESHOLD: float = config('RAG_SIMILARITY_THRESHOLD', default=0.35, cast=float)

# --- Embedding Config ---
EMBEDDING_MODEL: str = config('OPENAI_EMBEDDING_MODEL', default='text-embedding-3-small')
EMBEDDING_BATCH_SIZE: int = config('EMBEDDING_BATCH_SIZE', default=100, cast=int)

# --- LLM Config ---
OPENAI_MODEL: str = config('OPENAI_MODEL', default='gpt-4o')
OPENAI_API_KEY: str = config('OPENAI_API_KEY')
MAX_TOKENS: int = config('MAX_TOKENS', default=4000, cast=int)
TEMPERATURE: float = config('TEMPERATURE', default=0.3, cast=float)

# --- Index Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Store index at project root so it's NOT gitignored (media/ is gitignored).
# This file gets committed so Vercel bundles it.
INDEX_DIR: Path = BASE_DIR / 'data' / 'rag_index'
INDEX_DIR.mkdir(parents=True, exist_ok=True)

FAISS_INDEX_FILE: Path = INDEX_DIR / 'faiss_index.pkl'
METADATA_FILE: Path = INDEX_DIR / 'metadata.pkl'