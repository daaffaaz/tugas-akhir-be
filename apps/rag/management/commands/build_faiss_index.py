"""
Usage:
    python manage.py build_faiss_index

Builds the FAISS index from all active courses in the database.
Outputs:
    - data/rag_index/faiss_index.pkl   (committed to git for Vercel)
    - media/rag_index/faiss_index.pkl  (local working copy)
"""
import logging
import shutil
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.courses.models import Course
from apps.rag import chunker, config, embedder, index_store, vector_store

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Build FAISS index from all active courses in the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--index-dir', type=str, default=None,
            help='Override output directory for the index files.',
        )
        parser.add_argument(
            '--platform', type=str, default=None,
            help='Filter courses by platform name (e.g. "Coursera").',
        )
        parser.add_argument(
            '--limit', type=int, default=None,
            help='Limit number of courses to index (for testing).',
        )

    def handle(self, *args, **options):
        index_dir = Path(options['index_dir']) if options['index_dir'] else config.INDEX_DIR

        self.stdout.write('Fetching courses from DB...')
        queryset = (
            Course.objects
            .filter(is_active=True)
            .select_related('platform')
            .prefetch_related('tags')
            .order_by('created_at')
        )
        if options.get('platform'):
            queryset = queryset.filter(platform__name__iexact=options['platform'])
        if options.get('limit'):
            queryset = queryset[:options['limit']]

        courses = list(queryset)
        self.stdout.write(f'  → {len(courses)} active courses found.')

        if not courses:
            self.stderr.write(self.style.ERROR('No active courses found. Aborting.'))
            return

        self.stdout.write('Chunking courses...')
        chunks = chunker.courses_to_chunks(courses)
        texts = [c['text'] for c in chunks]
        self.stdout.write(f'  → {len(texts)} chunks created.')

        self.stdout.write(f'Embedding {len(texts)} chunks with {config.EMBEDDING_MODEL}...')
        embeddings = embedder.embed_texts(texts)
        self.stdout.write(f'  → {len(embeddings)} embeddings generated.')

        self.stdout.write('Building FAISS index...')
        index = vector_store.build_faiss_index(embeddings)
        self.stdout.write(f'  → Index built with {index.ntotal} vectors, dim={index.d}')

        self.stdout.write(f'Saving to {index_dir}...')
        index_store.save_faiss_index(index, chunks, path=index_dir / 'faiss_index.pkl')

        size_mb = (index_dir / 'faiss_index.pkl').stat().st_size / 1024 / 1024
        self.stdout.write(self.style.SUCCESS(
            f'Done. Index saved to {index_dir}/faiss_index.pkl ({size_mb:.2f} MB)'
        ))

        index_path = index_dir / 'faiss_index.pkl'
        data_dir = config.BASE_DIR / 'data' / 'rag_index'
        if index_dir != data_dir:
            data_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(index_path, data_dir / 'faiss_index.pkl')
            self.stdout.write(f'  Copied to {data_dir}/ for git deployment.')
        else:
            self.stdout.write(f'  Already at {data_dir}/ — no copy needed.')
