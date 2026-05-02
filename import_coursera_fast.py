"""
Fast bulk import for Coursera CSV.
Bypasses Django transaction overhead for speed.
"""
import csv
import uuid
import sys, os
sys.path.insert(0, '.')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
import django; django.setup()

from decimal import Decimal
from datetime import datetime
import re

from apps.courses.models import Course, Platform, Tag, CourseTag

# --- helpers ---
def parse_int(v):
    if not v or str(v).strip().upper() in ('N/A', 'NA', ''): return 0
    m = re.sub(r'[^\d]', '', str(v))
    return int(m) if m else 0

def parse_rating(v):
    if not v or str(v).strip().upper() in ('N/A', 'NA', ''): return Decimal('4.5')
    try: return Decimal(str(v).strip())
    except: return Decimal('4.5')

def parse_decimal(v):
    if not v or str(v).strip().upper() in ('N/A', 'NA', ''): return None
    try: return Decimal(str(v).replace(',',''))
    except: return None

def parse_date(v):
    if not v or str(v).strip().upper() in ('N/A', 'NA', ''): return None
    try: return datetime.strptime(str(v).strip()[:10], '%Y-%m-%d').date()
    except: return None

def extract_coursera_id(url):
    m = re.search(r'/learn/([^/?#]+)', str(url))
    return m.group(1) if m else str(url)[:255]

def split_tags(raw, delim=','):
    if not raw or str(raw).strip().upper() in ('N/A', 'NA', ''): return []
    return [t.strip() for t in str(raw).split(delim) if t.strip()]

# --- setup ---
platform, _ = Platform.objects.get_or_create(
    name='Coursera',
    defaults={'base_url': 'https://www.coursera.org', 'logo_url': ''}
)

# Clear existing coursera
existing = Course.objects.filter(platform=platform)
print(f"Deleting {existing.count()} existing Coursera courses...")
existing.delete()

# Read CSV
csv_path = "data/coursera_courses_100 copy.csv"
print(f"Reading {csv_path}...")

created = 0
tag_cache = {}

with open(csv_path, encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        title = (row.get('title') or '').strip()
        url = (row.get('url') or '').strip()
        ext_id = extract_coursera_id(url)

        if not title or not url:
            print(f"  Row {i+2}: skipping empty title/url")
            continue

        instructor = (row.get('instructor') or '').strip()
        if instructor.upper() == 'N/A': instructor = ''

        desc = (row.get('description') or '').strip()
        if desc.upper() == 'N/A': desc = ''

        wyl = (row.get('what_you_learn') or '').strip()
        if wyl.upper() == 'N/A': wyl = ''

        tag_raw = (row.get('tag') or '').strip()
        if tag_raw.upper() == 'N/A': tag_raw = ''

        course = Course.objects.create(
            platform=platform,
            external_id=ext_id,
            title=title[:500],
            instructor=instructor[:255],
            price=parse_decimal(row.get('price')) or Decimal('0'),
            reviews_count=parse_int(row.get('reviews_count')),
            rating=parse_rating(row.get('rating')),
            description=desc,
            duration=(row.get('duration') or '')[:200],
            video_hours=parse_decimal(row.get('video_hours')),
            reading_count=parse_int(row.get('reading_count')),
            assignment_count=parse_int(row.get('assignment_count')),
            what_you_learn=wyl,
            tag=tag_raw,
            url=url,
            thumbnail_url=(row.get('thumbnail_url') or '')[:500],
            level=(row.get('level') or '')[:80],
            scraped_date=parse_date(row.get('scraped_date')),
            scraped_at=None,
            currency='IDR',
            is_active=True,
        )

        # Tags
        for tag_name in split_tags(tag_raw):
            if tag_name not in tag_cache:
                tag_obj, _ = Tag.objects.get_or_create(name=tag_name[:120])
                tag_cache[tag_name] = tag_obj
            CourseTag.objects.get_or_create(course=course, tag=tag_cache[tag_name])

        created += 1
        if created % 20 == 0:
            print(f"  Imported {created} courses...")

print(f"\nDone! Created {created} Coursera courses.")