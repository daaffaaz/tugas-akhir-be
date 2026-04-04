import csv
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.courses.models import Course, CourseTag, Platform, Tag


def _parse_int_commas(value: str) -> int:
    if not value or str(value).strip().upper() in ('N/A', 'NA', ''):
        return 0
    cleaned = re.sub(r'[^\d]', '', str(value))
    return int(cleaned) if cleaned else 0


def _parse_rating(value: str):
    if not value or str(value).strip().upper() in ('N/A', 'NA', ''):
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None


def _parse_duration_hours(value: str):
    if not value or str(value).strip().upper() in ('N/A', 'NA', ''):
        return None
    m = re.search(r'([\d.]+)\s*hours?', str(value), re.I)
    if m:
        try:
            return Decimal(m.group(1))
        except (InvalidOperation, ValueError):
            return None
    return None


def _parse_price_currency(value: str):
    if not value:
        return None, 'IDR'
    s = str(value).strip()
    if s.upper() == 'FREE':
        return Decimal('0'), 'IDR'
    m = re.match(r'^([A-Z]{3})([\d.,]+)$', s.replace(' ', ''), re.I)
    if m:
        cur = m.group(1).upper()
        num = m.group(2).replace(',', '')
        try:
            return Decimal(num), cur
        except (InvalidOperation, ValueError):
            return None, 'IDR'
    try:
        return Decimal(s.replace(',', '')), 'IDR'
    except (InvalidOperation, ValueError):
        return None, 'IDR'


def _parse_scraped_at(value: str):
    if not value or str(value).strip().upper() in ('N/A', 'NA', ''):
        return None
    dt = parse_datetime(str(value).strip())
    if dt:
        if timezone.is_naive(dt):
            return timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    try:
        return datetime.strptime(str(value).strip(), '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return None


def _udemy_external_id(url: str) -> str:
    m = re.search(r'/course/([^/?#]+)', url or '')
    return m.group(1) if m else (url or '')[:255]


def _icei_external_id(url: str) -> str:
    if not url:
        return ''
    m = re.search(r'(course-v1:[^/?#]+)', url)
    if m:
        return m.group(1)[:255]
    return url[:255]


def _split_tags(raw: str) -> list[str]:
    if not raw or str(raw).strip().upper() in ('N/A', 'NA', ''):
        return []
    return [t.strip() for t in str(raw).split(';') if t.strip()]


class Command(BaseCommand):
    help = 'Import courses from scraped CSV (platform: udemy | icei).'

    def add_arguments(self, parser):
        parser.add_argument('--platform', type=str, required=True, choices=('udemy', 'icei'))
        parser.add_argument('--file', type=str, required=True, help='Path to CSV file')

    def handle(self, *args, **options):
        platform_key = options['platform']
        path = Path(options['file']).resolve()
        if not path.is_file():
            raise CommandError(f'File not found: {path}')

        platform_defaults = {
            'udemy': {
                'name': 'Udemy',
                'base_url': 'https://www.udemy.com',
            },
            'icei': {
                'name': 'ICEI',
                'base_url': 'https://icei.ac.id',
            },
        }
        pd = platform_defaults[platform_key]

        with path.open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            raise CommandError('CSV is empty.')

        with transaction.atomic():
            platform, _ = Platform.objects.get_or_create(
                name=pd['name'],
                defaults={'base_url': pd['base_url'], 'logo_url': ''},
            )

            created_courses = 0
            updated_courses = 0

            for row in rows:
                if platform_key == 'udemy':
                    res = self._import_udemy_row(platform, row)
                else:
                    res = self._import_icei_row(platform, row)
                if res is None:
                    continue
                _course, created = res
                if created:
                    created_courses += 1
                else:
                    updated_courses += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Processed {len(rows)} row(s). Created {created_courses}, updated {updated_courses}.',
            ),
        )

    def _import_udemy_row(self, platform: Platform, row: dict):
        url = (row.get('url') or '').strip()
        external_id = _udemy_external_id(url)
        title = (row.get('title') or '').strip()
        if not title or not url:
            return None

        price, currency = _parse_price_currency(row.get('price') or '')
        reviews_count = _parse_int_commas(row.get('reviews_count') or '')
        rating = _parse_rating(row.get('rating') or '')
        duration_hours = _parse_duration_hours(row.get('duration') or '')
        scraped_at = _parse_scraped_at(row.get('scraped_date') or '')
        difficulty = (row.get('level') or '').strip()

        defaults = {
            'title': title[:500],
            'description': (row.get('description') or '')[:],
            'url': url,
            'instructor_name': (row.get('instructor') or '')[:255],
            'price': price,
            'currency': currency[:3],
            'rating': rating,
            'review_count': reviews_count,
            'duration_hours': duration_hours,
            'difficulty_level': difficulty[:80],
            'scraped_at': scraped_at,
        }

        course, created = Course.objects.update_or_create(
            platform=platform,
            external_id=external_id,
            defaults=defaults,
        )
        self._sync_tags(course, row.get('tag') or '')
        return course, created

    def _import_icei_row(self, platform: Platform, row: dict):
        url = (row.get('link') or '').strip()
        external_id = _icei_external_id(url)
        title = (row.get('title') or '').strip()
        if not title or not url:
            return None

        price, currency = _parse_price_currency(row.get('price') or '')
        reviews_count = _parse_int_commas(row.get('reviews_count') or '')
        rating = _parse_rating(row.get('rating') or '')
        duration_hours = _parse_duration_hours(row.get('duration') or '')
        scraped_at = _parse_scraped_at(row.get('scraped_date') or '')
        difficulty = (row.get('level') or '').strip()

        defaults = {
            'title': title[:500],
            'description': (row.get('description') or '') if (row.get('description') or '').strip().upper() != 'N/A' else '',
            'url': url,
            'instructor_name': (row.get('instructor') or '')[:255] if (row.get('instructor') or '').upper() != 'N/A' else '',
            'price': price,
            'currency': currency[:3],
            'rating': rating,
            'review_count': reviews_count,
            'duration_hours': duration_hours,
            'difficulty_level': difficulty[:80],
            'scraped_at': scraped_at,
        }

        course, created = Course.objects.update_or_create(
            platform=platform,
            external_id=external_id,
            defaults=defaults,
        )
        self._sync_tags(course, row.get('tag') or '')
        return course, created

    def _sync_tags(self, course: Course, tag_raw: str):
        names = _split_tags(tag_raw)
        CourseTag.objects.filter(course=course).delete()
        for name in names:
            tag, _ = Tag.objects.get_or_create(name=name[:120])
            CourseTag.objects.get_or_create(course=course, tag=tag)
