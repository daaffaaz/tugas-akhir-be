"""
Replacement course generator — generates per-course AI explanation
for replace-course feature. Evaluates multiple candidates and picks the best.
"""
import logging

from openai import OpenAI

from apps.rag import config, context_builder

logger = logging.getLogger(__name__)

client = OpenAI(api_key=config.OPENAI_API_KEY)

REPLACE_SYSTEM_PROMPT = """You are an expert course advisor helping a user replace a course they didn't like.

Given:
1. The ORIGINAL course (the one being replaced) and WHY it's being replaced
2. 5-10 CANDIDATE courses (retrieved from the course database)
3. The user's learning context (profile + additional context)

Your task:
- For EACH candidate course, score how well it serves as a REPLACEMENT for the original.
- A good replacement matches the SAME learning goal but with a different approach:
  * Different instructor style / platform
  * Different teaching pace (faster/slower)
  * Different depth level
  * Different practical focus
  * Better reviews / better value

Respond with ONLY this JSON (no markdown, no extra text):
{{
  "replacement_for": "original course title",
  "replacement_reason_summary": "1-sentence why the user may not have liked the original",
  "candidates": [
    {{
      "course_id": "UUID from the candidate list",
      "score": 0.0-1.0,
      "match_reason": "2-4 sentence explanation why this is a good replacement",
      "best_for": "who should take this replacement",
      "potential_concerns": "1-2 sentences on what to watch out for with this replacement"
    }}
  ]
}}

Output JSON only:"""

REPLACE_USER_TEMPLATE = """## USER PROFILE:
{user_profile}

## COURSE BEING REPLACED:
{original_course_text}

## ADDITIONAL CONTEXT FROM USER (why they want to replace):
{additional_context}

## CANDIDATE COURSES (retrieved from database):
{courses_context}

## YOUR TASK:
Evaluate each candidate course as a REPLACEMENT for the original.
Consider:
- Does it cover a similar topic/skill?
- Is it at a similar or better level?
- Does it offer a different teaching approach?
- Is it compatible with the user's budget and time constraints?

Output JSON only:"""


def _build_replace_prompt(
    user_profile_text: str,
    original_course_text: str,
    additional_context: str,
    candidates_context: str,
) -> str:
    return REPLACE_USER_TEMPLATE.format(
        user_profile=user_profile_text,
        original_course_text=original_course_text,
        additional_context=additional_context or "No additional context provided.",
        courses_context=candidates_context,
    )


def _call_replace_llm(
    user_profile_text: str,
    original_course_text: str,
    additional_context: str,
    candidates_context: str,
) -> dict:
    prompt = _build_replace_prompt(
        user_profile_text, original_course_text, additional_context, candidates_context
    )

    try:
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": REPLACE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        logger.warning(f"[replace_generator] LLM call failed: {e}")
        return {
            "replacement_for": original_course_text[:80],
            "replacement_reason_summary": "AI unavailable.",
            "candidates": [],
        }

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        raw = raw.lstrip("json\n").rstrip("```").strip()

    try:
        import json
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"[replace_generator] Failed to parse JSON: {raw[:100]}")
        return {
            "replacement_for": original_course_text[:80],
            "replacement_reason_summary": "Parse error.",
            "candidates": [],
        }


def generate_replacement_explanations(
    topic: str,
    user_profile: dict,
    original_course_metadata: dict,
    candidate_courses: list[dict],
    additional_context: str = '',
) -> dict:
    """
    Generate replacement explanations for a set of candidate courses.

    Args:
        topic: the original search topic
        user_profile: full user profile dict
        original_course_metadata: metadata dict of the course being replaced
        candidate_courses: list of candidate metadata dicts to evaluate as replacements
        additional_context: user-provided reason for replacing

    Returns:
        dict with:
            - replacement_for: original course title
            - replacement_reason_summary: 1-sentence why user may not like original
            - candidates: list of scored+explained replacement candidates
              (each includes: course_id, score, match_reason, best_for, potential_concerns)
    """
    if not candidate_courses:
        return {
            "replacement_for": "",
            "replacement_reason_summary": "No candidates available.",
            "candidates": [],
        }

    user_profile_text = context_builder.build_user_profile_text(
        topic=topic,
        current_skills=user_profile.get('current_skills', []),
        goals=user_profile.get('goals', []),
        level=user_profile.get('level', ''),
        budget=user_profile.get('budget', None),
        weekly_hours=user_profile.get('weekly_hours', None),
        additional_context=additional_context,
    )

    original_course_text = context_builder.course_to_text(original_course_metadata)
    candidates_context = context_builder.courses_to_context(candidate_courses)

    result = _call_replace_llm(
        user_profile_text,
        original_course_text,
        additional_context,
        candidates_context,
    )

    # Merge FAISS scores into candidates
    score_map = {c.get('course_id'): c.get('_score', 0.0) for c in candidate_courses}
    meta_map = {c.get('course_id'): c for c in candidate_courses}

    enriched_candidates = []
    for cand in result.get('candidates', []):
        cid = cand.get('course_id')
        if cid in meta_map:
            meta = meta_map[cid]
            cand['faiss_score'] = score_map.get(cid, 0.0)
            # Merge course metadata
            m = meta.get('metadata', meta)
            cand['title'] = m.get('title')
            cand['instructor'] = m.get('instructor')
            cand['platform'] = m.get('platform')
            cand['level'] = m.get('level')
            cand['rating'] = m.get('rating')
            cand['price'] = m.get('price')
            cand['currency'] = m.get('currency')
            cand['duration'] = m.get('duration')
            cand['thumbnail_url'] = m.get('thumbnail_url')
            cand['url'] = m.get('url')
            enriched_candidates.append(cand)

    logger.info(
        f"[replace_generator] Generated {len(enriched_candidates)} replacement candidates"
    )
    return {
        "replacement_for": result.get('replacement_for', ''),
        "replacement_reason_summary": result.get('replacement_reason_summary', ''),
        "candidates": enriched_candidates,
    }
