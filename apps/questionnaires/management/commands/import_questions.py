import csv
import string
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.questionnaires.models import Question


def _options_to_json(raw: str) -> dict:
    parts = [p.strip() for p in raw.split(';') if p.strip()]
    letters = string.ascii_uppercase
    keys = []
    for i in range(len(parts)):
        if i < len(letters):
            keys.append(letters[i])
        else:
            keys.append(f'OPT{i + 1}')
    return dict(zip(keys, parts))


class Command(BaseCommand):
    help = 'Import questionnaire questions from CSV (columns: No, Kategori, Pertanyaan, Tipe Input, Opsi Jawaban, Variabel).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Path to CSV file (e.g. data/pertanyaan_kuesioner.csv)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete existing questions before import.',
        )

    def handle(self, *args, **options):
        path = Path(options['file']).resolve()
        if not path.is_file():
            raise CommandError(f'File not found: {path}')

        with path.open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            raise CommandError('CSV is empty.')

        with transaction.atomic():
            if options['clear']:
                deleted, _ = Question.objects.all().delete()
                self.stdout.write(self.style.WARNING(f'Deleted {deleted} existing question rows.'))

            for row in rows:
                no = row.get('No')
                if not no or not str(no).strip().isdigit():
                    continue
                order_number = int(str(no).strip())
                section = (row.get('Kategori') or '').strip()
                text = (row.get('Pertanyaan') or '').strip()
                input_type = (row.get('Tipe Input') or '').strip()
                options_raw = (row.get('Opsi Jawaban') or '').strip()
                variable_key = (row.get('Variabel Model (AI Feature)') or '').strip()

                options_json = _options_to_json(options_raw)

                Question.objects.update_or_create(
                    order_number=order_number,
                    defaults={
                        'section': section,
                        'question_text': text,
                        'input_type': input_type,
                        'options_json': options_json,
                        'variable_key': variable_key,
                    },
                )

        self.stdout.write(self.style.SUCCESS(f'Imported {len(rows)} question row(s) from {path}.'))
