import csv
import json
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
    help = 'Import questionnaire questions from CSV or JSON file.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='docs/questionnaire.json',
            help='Path to CSV or JSON file. Defaults to docs/questionnaire.json',
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

        suffix = path.suffix.lower()

        with path.open(encoding='utf-8') as f:
            raw = f.read()

        if suffix == '.json':
            rows = self._parse_json(raw)
        elif suffix == '.csv':
            rows = self._parse_csv(raw)
        else:
            raise CommandError(f'Unsupported file format: {suffix}. Use --file=.json or .csv')

        if not rows:
            raise CommandError('No question rows found in file.')

        with transaction.atomic():
            if options['clear']:
                deleted, _ = Question.objects.all().delete()
                self.stdout.write(self.style.WARNING(f'Deleted {deleted} existing question rows.'))

            created = 0
            updated = 0
            for row in rows:
                order_number = int(row['order'])
                section = row.get('section', '').strip()
                text = row.get('question_text', '').strip()
                input_type = row.get('input_type', '').strip()
                options_json = row.get('options_json', {})
                variable_key = row.get('variable_key', '').strip()
                is_active = row.get('is_active', True)

                obj, is_new = Question.objects.update_or_create(
                    order_number=order_number,
                    defaults={
                        'section': section,
                        'question_text': text,
                        'input_type': input_type,
                        'options_json': options_json,
                        'variable_key': variable_key,
                        'is_active': is_active,
                    },
                )
                if is_new:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done — {created} created, {updated} updated ({len(rows)} total rows).'
        ))

    # ── JSON parser ───────────────────────────────────────────────────────────

    def _parse_json(self, raw: str) -> list[dict]:
        """Parse docs/questionnaire.json format (v2 / v3)."""
        data = json.loads(raw)

        # Flatten all questions from all sections into a single list
        questions = []
        for section in data.get('sections', []):
            section_name = section.get('name', '')
            for q in section.get('questions', []):
                q = dict(q)
                q['section'] = section_name
                questions.append(q)

        return questions

    # ── CSV parser ───────────────────────────────────────────────────────────

    def _parse_csv(self, raw: str) -> list[dict]:
        """Parse CSV format (legacy, columns: No, Kategori, Pertanyaan, ...)."""
        import io
        reader = csv.DictReader(io.StringIO(raw))
        questions = []
        for row in reader:
            no = row.get('No')
            if not no or not str(no).strip().isdigit():
                continue
            order_number = int(str(no).strip())
            section = (row.get('Kategori') or '').strip()
            text = (row.get('Pertanyaan') or '').strip()
            input_type = (row.get('Tipe Input') or '').strip()
            options_raw = (row.get('Opsi Jawaban') or '').strip()
            variable_key = (row.get('Variabel Model (AI Feature)') or '').strip()

            questions.append({
                'order': order_number,
                'section': section,
                'question_text': text,
                'input_type': input_type,
                'options_json': _options_to_json(options_raw),
                'variable_key': variable_key,
                'is_active': True,
            })
        return questions
