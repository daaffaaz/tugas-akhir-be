"""
Usage:
    python manage.py build_faiss_index

Builds the FAISS index from all active courses in the database.
Outputs:
    - media/rag_index/faiss_index.pkl  (FAISS index binary)
    - media/rag_index/metadata.pkl     (list of course metadata dicts)
"""
import logging
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.courses.models import Course
from apps.rag import chunker, config, embedder, index_store, vector_store

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Build FAISS index from all active courses in the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--index-dir',
            type=str,
            default=None,
            help='Override output directory for the index files.',
        )
        parser.add_argument(
            '--platform',
            type=str,
            default=None,
            help='Filter courses by platform name (e.g. "Coursera").',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of courses to index (for testing).',
        )

    def handle(self, *args, **options):
        index_dir = Path(options['index_dir']) if options['index_dir'] else config.INDEX_DIR

        self.stdout.write(f'Fetching courses from DB...')
        queryset = Course.objects.filter(is_active=True).select_related('platform').prefetch_related('tags')
        queryset = queryset.order_by('created_at')

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

        self.stdout.write('Building embeddings index...')
        index = vector_store.build_faiss_index(embeddings)
        self.stdout.write(f'  → Index built with {index.shape[0]} vectors, dim={index.shape[1]}')

        self.stdout.write(f'Saving to {index_dir}...')
        index_store.save_faiss_index(index, chunks, path=index_dir / 'faiss_index.pkl')
        self.stdout.write(
            self.style.SUCCESS(
                f'Done. Index saved to {index_dir}/faiss_index.pkl'
            ),
        )
        self.stdout.write(
            f'  Index size: {(index_dir / "faiss_index.pkl").stat().st_size / 1024 / 1024:.2f} MB'
        )

        # Also copy to media/rag_index/ for git commit (Vercel deployment)
        media_dir = config.BASE_DIR / 'media' / 'rag_index'
        media_dir.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(index_dir / 'faiss_index.pkl', media_dir / 'faiss_index.pkl')
        self.stdout.write(
            self.style.SUCCESS(f'  Copied to {media_dir}/ for git deployment.')
        )
