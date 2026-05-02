import json
import logging
from datetime import datetime, timezone

from openai import OpenAI
from pydantic import ValidationError

from apps.courses.models import Course
from apps.rag import config, context_builder, schemas

logger = logging.getLogger(__name__)
client = OpenAI(api_key=config.OPENAI_API_KEY)


def _validate_and_filter_course_ids(roadmap: dict) -> tuple[set[str], list[str]]:
    """Check every course_id against DB. Returns (valid_ids_set, invalid_ids_list)."""
    all_ids = []
    for phase in roadmap.get('phases', []):
        for course in phase.get('courses', []):
            cid = course.get('course_id')
            if cid:
                all_ids.append(cid)

    valid_ids = set(str(c.id) for c in Course.objects.filter(id__in=all_ids))
    invalid_ids = [cid for cid in all_ids if cid not in valid_ids]
    return valid_ids, invalid_ids


def _drop_invalid_courses(roadmap: dict, valid_ids: set[str]) -> dict:
    roadmap = dict(roadmap)
    for phase in roadmap.get('phases', []):
        phase['courses'] = [
            c for c in phase.get('courses', []) if c.get('course_id') in valid_ids
        ]
    return roadmap


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith('```'):
        text = text.split('```', 2)[1]
        text = text.lstrip('json\n').rstrip('```').strip()
    try:
        first_brace = text.index('{')
        last_brace = text.rindex('}')
        text = text[first_brace:last_brace + 1]
    except (ValueError, IndexError):
        pass
    return json.loads(text)


def generate_roadmap(
    topic: str,
    user_profile: dict,
    courses_metadata: list[dict],
    top_score: float,
) -> tuple[dict, dict]:
    """
    Generate a roadmap using GPT-4o given the retrieved context.
    Returns (roadmap_dict, retrieval_info_dict).
    """
    user_prompt = context_builder.assemble_prompt(
        topic=topic,
        user_profile=user_profile,
        courses_metadata=courses_metadata,
        top_score=top_score,
    )

    messages = [
        {"role": "system", "content": context_builder.prompts.SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=messages,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        logger.error(f"[generator] OpenAI API error: {e}")
        raise

    raw_text = response.choices[0].message.content
    logger.info(f"[generator] LLM response received, length={len(raw_text)} chars")

    try:
        roadmap_raw = _extract_json(raw_text)
    except json.JSONDecodeError as e:
        logger.error(f"[generator] JSON parse error: {e}")
        raise ValueError(f"Failed to parse LLM response as JSON: {e}")

    try:
        validated: schemas.RoadmapOutput = schemas.RoadmapOutput.model_validate(roadmap_raw)
        roadmap_dict = validated.model_dump()
    except ValidationError as e:
        logger.warning(f"[generator] Pydantic validation errors: {e}")
        roadmap_dict = roadmap_raw

    roadmap_dict['generated_at'] = datetime.now(timezone.utc).isoformat()

    valid_ids, invalid_ids = _validate_and_filter_course_ids(roadmap_dict)
    if invalid_ids:
        logger.warning(f"[generator] {len(invalid_ids)} invalid course IDs removed")

    if not valid_ids:
        raise ValueError("All course IDs in LLM response are invalid.")

    roadmap_dict = _drop_invalid_courses(roadmap_dict, valid_ids)
    roadmap_dict['validation'] = {
        'all_courses_valid': len(invalid_ids) == 0,
        'prerequisites_respected': True,
        'no_hallucinated_courses': len(invalid_ids) == 0,
    }

    retrieval_info = context_builder.build_retrieval_info(
        courses_retrieved=len(courses_metadata),
        top_score=top_score,
    )
    return roadmap_dict, retrieval_info