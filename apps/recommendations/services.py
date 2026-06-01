import json
import logging

from django.db.models import Q

from apps.courses.models import Course
from apps.learning_paths.models import LearningPathCourse
from apps.rag.config import MAX_TOKENS, OPENAI_MODEL, TEMPERATURE
from apps.rag.generator import client as openai_client
from apps.rag.retriever import retrieve_courses

from .prompts import NEXT_STEPS_SYSTEM_PROMPT, build_next_steps_user_prompt

logger = logging.getLogger(__name__)

MIN_CAREER_POSSIBILITIES = 2
MAX_CAREER_POSSIBILITIES = 4
MIN_SUGGESTED_COURSES = 3
MAX_SUGGESTED_COURSES = 5
MAX_COMPLETED_COURSES_IN_PROMPT = 10


def _format_completed_courses_block(items: list[LearningPathCourse]) -> str:
    """Render up to N completed courses as a readable block for the LLM prompt."""
    selected = items[:MAX_COMPLETED_COURSES_IN_PROMPT]
    lines = []
    for lpc in selected:
        course = lpc.course
        tags = ', '.join(t.name for t in course.tags.all()) or 'None'
        desc = (course.description or '')[:200]
        lines.append(
            f"- {course.title} | Level: {course.level or 'N/A'} | "
            f"Tags: {tags} | Description: {desc}"
        )
    return '\n'.join(lines) if lines else 'No completed courses.'


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith('```'):
        parts = text.split('```', 2)
        if len(parts) >= 2:
            text = parts[1]
            if text.startswith('json'):
                text = text[4:]
            text = text.strip()
    try:
        first_brace = text.index('{')
        last_brace = text.rindex('}')
        text = text[first_brace:last_brace + 1]
    except ValueError:
        pass
    return json.loads(text)


def _generate_career_possibilities(completed_items: list[LearningPathCourse]) -> dict:
    """Call GPT-4o with JSON mode, return parsed dict (or raise)."""
    completed_block = _format_completed_courses_block(completed_items)
    user_prompt = build_next_steps_user_prompt(completed_block)

    response = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": NEXT_STEPS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        response_format={"type": "json_object"},
    )

    raw_text = response.choices[0].message.content
    logger.info(
        f"[next-steps] LLM response received, length={len(raw_text)} chars"
    )
    return _extract_json(raw_text)


def _normalize_confidence(value) -> float:
    try:
        conf = float(value)
    except (TypeError, ValueError):
        conf = 0.0
    return max(0.0, min(1.0, round(conf, 3)))


def _resolve_suggested_courses(
    course_titles: list[str],
    completed_course_ids: set[str],
    topics_for_retrieval: list[str],
) -> list[Course]:
    """
    Resolve a list of course titles to real Course instances, in order.

    Strategy:
    1. Try exact (case-insensitive) title match in DB.
    2. Try substring match in DB.
    3. Fallback: FAISS retrieval for the role + first topic, excluding completed.
    4. De-duplicate, exclude completed, cap at MAX_SUGGESTED_COURSES.
    """
    seen_ids: set[str] = set()
    resolved: list[Course] = []

    for title in course_titles:
        if len(resolved) >= MAX_SUGGESTED_COURSES:
            break
        if not title or not title.strip():
            continue

        # 1. Exact (case-insensitive) match
        qs = Course.objects.filter(
            title__iexact=title.strip(),
            is_active=True,
        ).exclude(id__in=completed_course_ids).exclude(id__in=seen_ids)
        course = qs.first()
        if not course:
            # 2. Substring match
            qs = Course.objects.filter(
                title__icontains=title.strip()[:40],
                is_active=True,
            ).exclude(id__in=completed_course_ids).exclude(id__in=seen_ids)
            course = qs.first()

        if course:
            resolved.append(course)
            seen_ids.add(str(course.id))
            continue

        # 3. FAISS fallback
        try:
            candidates, _ = retrieve_courses(title.strip(), user_profile=None, top_k=5)
            for cand in candidates:
                cid = cand.get('course_id')
                if not cid or cid in completed_course_ids or cid in seen_ids:
                    continue
                course = Course.objects.filter(id=cid, is_active=True).first()
                if course:
                    resolved.append(course)
                    seen_ids.add(cid)
                    if len(resolved) >= MAX_SUGGESTED_COURSES:
                        break
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[next-steps] FAISS fallback failed for '{title}': {e}")

    return resolved


def get_next_steps_for_user(user) -> dict:
    """
    Build the full next-steps response payload for a user.

    Returns dict with keys: career_possibilities, based_on.{completed_courses,reasoning}.
    """
    completed_items = list(
        LearningPathCourse.objects
        .filter(learning_path__user=user, is_completed=True)
        .select_related('course__platform')
        .prefetch_related('course__tags')
        .order_by('-completed_at')
    )

    based_on_completed = [
        {
            'course_id': str(item.course.id),
            'title': item.course.title,
            'completed_at': (
                item.completed_at.isoformat() if item.completed_at else None
            ),
        }
        for item in completed_items
    ]

    if not completed_items:
        return {
            'career_possibilities': [],
            'based_on': {
                'completed_courses': [],
                'reasoning': '',
            },
        }

    completed_course_ids = {str(item.course.id) for item in completed_items}

    try:
        llm_result = _generate_career_possibilities(completed_items)
    except Exception as e:
        logger.error(f"[next-steps] LLM generation failed: {e}")
        return {
            'career_possibilities': [],
            'based_on': {
                'completed_courses': based_on_completed,
                'reasoning': '',
            },
        }

    raw_possibilities = llm_result.get('career_possibilities', []) or []
    reasoning = llm_result.get('reasoning', '') or ''

    # Truncate to max 4, sort by confidence desc
    raw_possibilities = sorted(
        raw_possibilities,
        key=lambda x: _normalize_confidence(x.get('confidence', 0)),
        reverse=True,
    )[:MAX_CAREER_POSSIBILITIES]

    career_possibilities = []
    for raw in raw_possibilities:
        role = (raw.get('role') or '').strip()
        description = (raw.get('description') or '').strip()
        if not role:
            continue
        confidence = _normalize_confidence(raw.get('confidence', 0.0))
        course_titles = raw.get('course_titles', []) or []

        suggested = _resolve_suggested_courses(
            course_titles=course_titles,
            completed_course_ids=completed_course_ids,
            topics_for_retrieval=course_titles,
        )
        # Enforce minimum 3 by topping up with FAISS if needed
        if len(suggested) < MIN_SUGGESTED_COURSES:
            try:
                fillers, _ = retrieve_courses(role, user_profile=None, top_k=10)
                for cand in fillers:
                    cid = cand.get('course_id')
                    if not cid or cid in completed_course_ids:
                        continue
                    if any(str(s.id) == cid for s in suggested):
                        continue
                    course = Course.objects.filter(id=cid, is_active=True).first()
                    if course:
                        suggested.append(course)
                        if len(suggested) >= MIN_SUGGESTED_COURSES:
                            break
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[next-steps] FAISS top-up failed for '{role}': {e}")

        suggested = suggested[:MAX_SUGGESTED_COURSES]

        career_possibilities.append({
            'role': role,
            'confidence': confidence,
            'description': description,
            'suggested_courses': suggested,
        })

    return {
        'career_possibilities': career_possibilities,
        'based_on': {
            'completed_courses': based_on_completed,
            'reasoning': reasoning,
        },
    }
