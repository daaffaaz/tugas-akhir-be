"""
OpenRouter client for LLM-as-Judge evaluation.

Uses the OpenRouter API (OpenAI-compatible) to call multiple models
for scoring RAG output quality.
"""

import json
import logging
import time

from openai import OpenAI

from apps.rag import config
from apps.rag.context_builder import course_to_text

logger = logging.getLogger(__name__)

_judge_client = None


def _get_judge_client():
    global _judge_client
    if _judge_client is None:
        _judge_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=config.OPENROUTER_API_KEY,
            timeout=60.0,
        )
    return _judge_client


def _extract_json(text):
    """Extract JSON from LLM response text.

    Handles:
      - markdown code fences (```json ... ```)
      - reasoning-style outputs where JSON appears mid-text
      - trailing prose after JSON
    Raises json.JSONDecodeError if no valid JSON object is found.
    """
    text = text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        parts = text.split("```", 2)
        if len(parts) >= 2:
            inner = parts[1]
            if inner.startswith("json"):
                inner = inner[4:]
            text = inner.strip()
        if text.endswith("```"):
            text = text[:-3].strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find the first '{' and try parsing from there, increasing the window
    first_brace = text.find("{")
    if first_brace < 0:
        raise json.JSONDecodeError("No JSON object found", text, 0)

    # Try to find a balanced JSON object
    depth = 0
    in_string = False
    escape = False
    quote_char = None
    for i in range(first_brace, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if in_string:
            if ch == quote_char:
                in_string = False
            continue
        if ch in ('"', "'"):
            in_string = True
            quote_char = ch
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[first_brace : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    pass  # try the next closing brace

    # Final fallback: take from first { to last }
    last_brace = text.rfind("}")
    if last_brace > first_brace:
        return json.loads(text[first_brace : last_brace + 1])

    raise json.JSONDecodeError("No balanced JSON object found", text, 0)


def _format_user_profile(profile: dict | None) -> str:
    """Render a user_profile dict as a readable block for the judge prompt."""
    if not profile:
        return "(no user profile provided — judge should expect generic output)"

    lines = []
    if profile.get("level"):
        lines.append(f"  Level: {profile['level']}")
    if profile.get("current_skills"):
        skills = profile["current_skills"]
        if isinstance(skills, list):
            lines.append(f"  Current Skills: {', '.join(str(s) for s in skills)}")
        else:
            lines.append(f"  Current Skills: {skills}")
    if profile.get("goals"):
        goals = profile["goals"]
        if isinstance(goals, list):
            lines.append(f"  Goals: {', '.join(str(g) for g in goals)}")
        else:
            lines.append(f"  Goals: {goals}")
    if profile.get("budget") is not None:
        lines.append(f"  Budget: {profile['budget']}")
    if profile.get("weekly_hours"):
        lines.append(f"  Weekly Hours: {profile['weekly_hours']}")
    if profile.get("material_format"):
        lines.append(f"  Preferred Format: {profile['material_format']}")
    if profile.get("theory_practice"):
        lines.append(f"  Theory vs Practice: {profile['theory_practice']}")
    if profile.get("main_goal"):
        lines.append(f"  Main Goal: {profile['main_goal']}")
    if profile.get("certification_importance"):
        lines.append(f"  Certification Importance: {profile['certification_importance']}")
    if profile.get("additional_context"):
        lines.append(f"  Additional Context: {profile['additional_context']}")

    return "\n".join(lines) if lines else "(empty profile)"


SYSTEM_PROMPT = (
    "You are an expert AI evaluation judge for a career recommendation RAG system. "
    "Score the system output on 4 dimensions, each 1-5. "
    "You will receive: the user's query, the user's profile, the retrieved courses "
    "(with full metadata), and the generated roadmap. "
    "Reply with a single JSON object only. No prose, no markdown, no preamble. "
    "Schema: {\"relevance\": int 1-5, \"accuracy\": int 1-5, \"quality\": int 1-5, "
    "\"personalization\": int 1-5, \"reasoning\": str}. "
    "Keep the reasoning string under 60 words."
)

USER_PROMPT_TEMPLATE = (
    "## USER QUERY\n"
    "{query}\n\n"
    "## USER PROFILE\n"
    "{user_profile}\n\n"
    "## RETRIEVED COURSES\n"
    "{courses_json}\n\n"
    "## GENERATED ROADMAP\n"
    "{roadmap_json}\n\n"
    "## SCORING RUBRIC\n"
    "1. Relevance (1-5): How well does the output address the user's query intent?\n"
    "2. Accuracy (1-5): Are course details correct? No hallucinated courses or facts?\n"
    "3. Quality (1-5): Is the roadmap well-structured with logical progression and meaningful explanations?\n"
    "4. Personalization (1-5): Does it consider user's level, goals, and learning preferences?\n\n"
    "Output JSON only:\n"
    "{{\"relevance\": 0, \"accuracy\": 0, \"quality\": 0, \"personalization\": 0, \"reasoning\": \"\"}}"
)


def call_judge(model_id, query, courses, roadmap, user_profile=None, max_retries=1):
    """
    Score a single RAG output using one judge model.

    Args:
        model_id: OpenRouter model ID (e.g. 'openai/gpt-5.2')
        query: user's search query
        courses: list of retrieved course dicts
        roadmap: generated roadmap dict
        user_profile: dict of user profile fields (level, skills, goals, etc.)
        max_retries: number of additional retries on failure

    Returns:
        dict with keys: model, relevance, accuracy, quality, personalization, reasoning, scores
        Returns a zeroed dict on repeated failure.
    """
    # Use the same course-to-text formatter as production (apps/rag/context_builder.py)
    # so judges see full metadata: instructor, level, duration, rating, description, etc.
    course_blocks = [course_to_text(c) for c in courses[:12]]
    courses_json = "\n\n".join(course_blocks) if course_blocks else "(no courses retrieved)"

    # Truncate roadmap generously so judges see all phases.
    roadmap_json = json.dumps(roadmap, indent=2, ensure_ascii=False, default=str)[:20000]

    user_profile_text = _format_user_profile(user_profile)

    user_prompt = USER_PROMPT_TEMPLATE.format(
        query=query,
        user_profile=user_profile_text,
        courses_json=courses_json,
        roadmap_json=roadmap_json,
    )

    client = _get_judge_client()

    # Some OpenRouter models reject unknown params (e.g. some Gemma variants)
    # so we only attach response_format when the model is known to support it.
    supports_json_mode = any(
        tag in model_id.lower()
        for tag in ("gpt", "claude", "gemini", "mistral", "qwen", "llama", "command")
    )

    for attempt in range(max_retries + 1):
        try:
            create_kwargs = dict(
                model=model_id,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=config.JUDGE_TEMPERATURE,
                max_tokens=config.JUDGE_MAX_TOKENS,
            )
            if supports_json_mode:
                create_kwargs["response_format"] = {"type": "json_object"}

            try:
                response = client.chat.completions.create(**create_kwargs)
            except Exception as inner:
                # If response_format is rejected, retry without it
                if "response_format" in create_kwargs:
                    logger.debug(
                        f"[judge] {model_id} rejected response_format, retrying without: {inner}"
                    )
                    create_kwargs.pop("response_format", None)
                    response = client.chat.completions.create(**create_kwargs)
                else:
                    raise

            raw = response.choices[0].message.content.strip()
            parsed = _extract_json(raw)

            safe = lambda k: max(0, min(5, int(parsed.get(k) or 0)))
            rel = safe("relevance")
            acc = safe("accuracy")
            qua = safe("quality")
            per = safe("personalization")
            avg = (rel + acc + qua + per) / 4.0
            logger.info(
                f"[judge] {model_id} | query='{query[:40]}' | "
                f"rel={rel} acc={acc} qua={qua} per={per} | avg={avg:.2f}"
            )
            return {
                "model": model_id,
                "relevance": rel,
                "accuracy": acc,
                "quality": qua,
                "personalization": per,
                "reasoning": parsed.get("reasoning", ""),
                "scores": avg,
            }

        except Exception as e:
            logger.warning(f"[judge] {model_id} attempt {attempt+1}/{max_retries+1} failed: {e}")
            if attempt < max_retries:
                time.sleep(2)
            else:
                logger.error(f"[judge] {model_id} giving up after {max_retries+1} attempts: {e}")
                return {
                    "model": model_id,
                    "relevance": 0,
                    "accuracy": 0,
                    "quality": 0,
                    "personalization": 0,
                    "reasoning": f"Error: {e}",
                    "scores": 0,
                }

    return None


def score_all_models(query, courses, roadmap, user_profile=None):
    """
    Score a RAG output using all configured judge models.

    Args:
        query: user's search query
        courses: list of retrieved course dicts
        roadmap: generated roadmap dict
        user_profile: dict of user profile fields (level, skills, goals, etc.)

    Returns:
        list of judge result dicts (one per model)
    """
    results = []
    for model_id in config.JUDGE_MODELS:
        result = call_judge(model_id, query, courses, roadmap, user_profile=user_profile)
        if result:
            results.append(result)
    return results
