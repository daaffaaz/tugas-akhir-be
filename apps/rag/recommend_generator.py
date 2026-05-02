"""
Recommendation generator — generates per-course AI explanation.
Each course gets a short, human-readable explanation of WHY it fits the user.
"""
import logging

from openai import OpenAI

from apps.rag import config, context_builder

logger = logging.getLogger(__name__)

client = OpenAI(api_key=config.OPENAI_API_KEY)


# ---------------------------------------------------------------
# System / User prompts for per-course explanation
# ---------------------------------------------------------------

EXPLAIN_SYSTEM_PROMPT = """You are an expert course advisor.
Given the user profile and ONE candidate course, produce a short, honest explanation
of WHY this course fits (or doesn't fit) this specific user.
Be specific: mention skill level, learning goals, format preference, time commitment,
or budget if relevant. Do NOT invent facts not present in the course data.
Keep it to 2-4 sentences. Output valid JSON only."""

EXPLAIN_USER_TEMPLATE = """## USER PROFILE:
{user_profile}

## COURSE TO EVALUATE:
{course_text}

## YOUR TASK:
Respond with ONLY this JSON (no markdown, no extra text):
{{
  "match_score": 0.0-1.0,
  "match_reason": "2-4 sentence explanation why this course fits this user",
  "best_for": "short label who this course is best for",
  "potential_gaps": "1-2 sentence note on what this course does NOT cover"
}}

Output JSON only:"""


def _build_explain_prompt(user_profile_text: str, course_text: str) -> str:
    return EXPLAIN_USER_TEMPLATE.format(
        user_profile=user_profile_text,
        course_text=course_text,
    )


def _call_explain_llm(user_profile_text: str, course_text: str) -> dict:
    """
    Call GPT-4o to get per-course explanation.
    Returns dict with match_score, match_reason, best_for, potential_gaps.
    """
    prompt = _build_explain_prompt(user_profile_text, course_text)

    try:
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": EXPLAIN_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        logger.warning(f"[recommend_generator] LLM call failed: {e}")
        return {
            "match_score": 0.5,
            "match_reason": "Penjelasan tidak tersedia.",
            "best_for": "General learners",
            "potential_gaps": "Tidak ada informasi tambahan.",
        }

    raw = response.choices[0].message.content.strip()

    # Strip markdown code block if present
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        raw = raw.lstrip("json\n").rstrip("```").strip()

    try:
        import json
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"[recommend_generator] Failed to parse JSON: {raw[:100]}")
        return {
            "match_score": 0.5,
            "match_reason": "Penjelasan tidak tersedia.",
            "best_for": "General learners",
            "potential_gaps": "Tidak ada informasi tambahan.",
        }


# ---------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------

def generate_recommendations(
    topic: str,
    user_profile: dict,
    courses_metadata: list[dict],
) -> list[dict]:
    """
    Generate per-course AI explanations for each course in courses_metadata.

    Args:
        topic: the search topic (used in user profile text)
        user_profile: full user profile dict from _build_user_profile
        courses_metadata: list of course metadata dicts (from retriever)

    Returns:
        list of dicts, each containing the course metadata PLUS:
            - relevance_score  (FAISS score)
            - ai_explanation   (match_reason from LLM)
            - match_score      (0.0-1.0 LLM confidence)
            - best_for         (who this course is best for)
            - potential_gaps   (what course doesn't cover)
    """
    if not courses_metadata:
        return []

    # Build profile text once (same for all courses)
    user_profile_text = context_builder.build_user_profile_text(
        topic=topic,
        current_skills=user_profile.get('current_skills', []),
        goals=user_profile.get('goals', []),
        level=user_profile.get('level', ''),
        budget=user_profile.get('budget', None),
        weekly_hours=user_profile.get('weekly_hours', None),
        additional_context=user_profile.get('additional_context', ''),
    )

    results = []
    for course_meta in courses_metadata:
        course_text = context_builder.course_to_text(course_meta)
        explanation = _call_explain_llm(user_profile_text, course_text)

        result = dict(course_meta)
        result['relevance_score'] = course_meta.get('_score', 0.0)
        result['ai_explanation'] = explanation.get('match_reason', 'Penjelasan tidak tersedia.')
        result['match_score'] = explanation.get('match_score', 0.5)
        result['best_for'] = explanation.get('best_for', 'General learners')
        result['potential_gaps'] = explanation.get('potential_gaps', '')
        results.append(result)

    logger.info(f"[recommend_generator] Generated explanations for {len(results)} courses")
    return results
