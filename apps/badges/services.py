"""
Service layer untuk badge matching & awarding.

`evaluate_course_for_badges` adalah entrypoint utama yang dipanggil dari
view toggle-complete saat sebuah course berubah menjadi `is_completed=True`.
"""
from __future__ import annotations

import re
from typing import Iterable

from django.db import transaction

from .models import Badge, UserBadge


def _normalize(value: str) -> str:
    return (value or '').strip().lower()


def _course_tag_names(course) -> set[str]:
    return {_normalize(t.name) for t in course.tags.all() if t.name}


def _word_match(needle: str, haystack: str) -> bool:
    """
    Word-boundary regex match. Avoids false positives seperti
    "go" cocok dengan "google" atau "ai" cocok dengan "main".
    """
    if not needle or not haystack:
        return False
    pattern = r'\b' + re.escape(needle) + r'\b'
    return re.search(pattern, haystack) is not None


def _criteria_tags_match(course_tag_names: set[str], tags_any: Iterable[str]) -> bool:
    """
    Word-boundary matching, case-insensitive. Sebuah course cocok dengan badge
    kalau ada minimal 1 keyword di `tags_any` yang muncul sebagai kata utuh
    di salah satu tag course.

    Contoh:
      - keyword "ui/ux" cocok dengan tag "UI/UX Design"      -> True
      - keyword "react" cocok dengan tag "React JS"          -> True
      - keyword "go" cocok dengan tag "Google Cloud"         -> False (bukan kata utuh)
      - keyword "mobile development" cocok dengan tag "development" -> False
    """
    keywords = [_normalize(k) for k in tags_any if k]
    if not keywords:
        return True
    for tag_name in course_tag_names:
        if not tag_name:
            continue
        for keyword in keywords:
            if _word_match(keyword, tag_name):
                return True
    return False


def _criteria_level_match(course_level: str, level_any: Iterable[str]) -> bool:
    keywords = [_normalize(l) for l in level_any if l]
    if not keywords:
        return True
    if not course_level:
        return False
    return any(_word_match(k, course_level) for k in keywords)


def match_course_to_badges(course) -> list[Badge]:
    """
    Apply each active badge's `criteria` JSON against the course attributes.
    Returns list of Badge instances that match the course.
    """
    if course is None:
        return []
    tag_names = _course_tag_names(course)
    level_text = _normalize(course.level)

    matches: list[Badge] = []
    for badge in Badge.objects.filter(is_active=True):
        criteria = badge.criteria or {}
        tags_any = criteria.get('tags_any', []) or []
        level_any = criteria.get('level_any', []) or []
        if not _criteria_tags_match(tag_names, tags_any):
            continue
        if not _criteria_level_match(level_text, level_any):
            continue
        matches.append(badge)
    return matches


def evaluate_course_for_badges(user, course, learning_path=None) -> dict:
    """
    Dipanggil saat user menyelesaikan sebuah course.

    Untuk setiap badge yang match terhadap course:
      - Kalau user belum punya UserBadge tsb -> buat baru -> masuk `awarded`.
      - Kalau user sudah punya -> tidak duplikat -> masuk `already_owned` (warning ke FE).

    Returns:
        {
            "awarded": [Badge, ...],
            "already_owned": [Badge, ...],
        }
    """
    if user is None or not getattr(user, 'is_authenticated', False) or course is None:
        return {'awarded': [], 'already_owned': []}

    matched = match_course_to_badges(course)
    if not matched:
        return {'awarded': [], 'already_owned': []}

    awarded: list[Badge] = []
    already_owned: list[Badge] = []

    with transaction.atomic():
        for badge in matched:
            _, created = UserBadge.objects.get_or_create(
                user=user,
                badge=badge,
                defaults={
                    'earned_via_course': course,
                    'earned_via_learning_path': learning_path,
                },
            )
            if created:
                awarded.append(badge)
            else:
                already_owned.append(badge)

    return {'awarded': awarded, 'already_owned': already_owned}
