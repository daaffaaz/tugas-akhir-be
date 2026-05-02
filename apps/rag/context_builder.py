import textwrap

from apps.rag import config, knowledge_graph, prompts


def course_to_text(course_meta: dict) -> str:
    """
    Format a single course metadata dict as a readable block for the prompt.

    Metadata is stored NESTED under 'metadata' key in the FAISS index entry:
      {
        'course_id': '...',
        'text': '...',
        'metadata': { 'title': ..., 'instructor': ..., ... }
      }
    """
    # Resolve nested metadata
    meta = course_meta.get('metadata', course_meta)

    hours = meta.get('video_hours')
    duration = meta.get('duration', 'N/A')
    tags = meta.get('tags', '')

    lines = [
        f"— {meta.get('title', 'Unknown')} [ID: {course_meta.get('course_id', '')}]",
        f"  Instructor: {meta.get('instructor', 'N/A')}",
        f"  Level: {meta.get('level', 'N/A')} | Duration: {duration} | Hours: {hours or 'N/A'}h",
        f"  Rating: {meta.get('rating', 'N/A')}/5 ({meta.get('reviews_count', 0)} reviews)",
        f"  Price: {meta.get('currency', 'IDR')} {meta.get('price', 'Free')}",
        f"  Tags: {tags}" if tags else "",
    ]

    desc = meta.get('description', '')
    if desc:
        lines.append(f"  Description: {textwrap.shorten(desc, width=300, placeholder='...')}")

    learn = meta.get('what_you_learn', '')
    if learn:
        lines.append(f"  What You'll Learn: {textwrap.shorten(learn, width=200, placeholder='...')}")

    return '\n'.join(l for l in lines if l)


def courses_to_context(courses_metadata: list[dict]) -> str:
    """
    Format a list of course metadata dicts into a readable context block.
    Only includes the top RAG_MAX_CONTEXT_COURSES to stay within token budget.
    """
    max_courses = config.RAG_MAX_CONTEXT_COURSES
    selected = courses_metadata[:max_courses]

    header = f"[AVAILABLE COURSES — {len(selected)} courses]\n"
    blocks = [course_to_text(c) for c in selected]
    return header + '\n\n'.join(blocks)


def build_retrieval_info(courses_retrieved: int, top_score: float) -> dict:
    """Build the retrieval_info dict that gets injected into the output schema."""
    return {
        'courses_retrieved': courses_retrieved,
        'top_similarity_score': round(top_score, 3),
        'retrieval_method': 'semantic vector search + tag-based ordering',
    }


def build_user_profile_text(
    topic: str,
    current_skills: list[str],
    goals: list[str],
    level: str,
    budget,  # Can be int, str, or None
    weekly_hours,  # Can be str (e.g. "<4") or None
    additional_context: str = '',
) -> str:
    """Build a concise user profile string for the prompt."""
    # Handle budget: can be int or string like "<500k"
    if budget and str(budget).isdigit():
        budget_str = 'IDR {:,}'.format(int(budget))
    else:
        budget_str = str(budget) if budget else 'Not specified'

    lines = [
        f"Topic/Goal: {topic}",
        f"Current Skills: {', '.join(current_skills) if current_skills else 'None specified'}",
        f"Target Skills: {', '.join(goals) if goals else 'Not specified'}",
        f"Preferred Level: {level or 'Any'}",
        f"Weekly Study Hours: {weekly_hours or 'Not specified'}",
        f"Budget: {budget_str}",
    ]

    if additional_context:
        lines.append(f"Additional Context from User: {additional_context}")

    return '\n'.join(lines)


def assemble_prompt(
    topic: str,
    user_profile: dict,
    courses_metadata: list[dict],
    top_score: float,
) -> str:
    """
    Full prompt assembly: system + user message.
    Returns the fully assembled user prompt string.
    """
    profile_text = build_user_profile_text(
        topic=topic,
        current_skills=user_profile.get('current_skills', []),
        goals=user_profile.get('goals', []),
        level=user_profile.get('level', ''),
        budget=user_profile.get('budget', None),
        weekly_hours=user_profile.get('weekly_hours', None),
        additional_context=user_profile.get('additional_context', ''),
    )

    courses_context = courses_to_context(courses_metadata)
    prereq_chain = knowledge_graph.build_prereq_chain(courses_metadata)

    return prompts.build_user_prompt(
        topic=topic,
        user_profile=profile_text,
        courses_context=courses_context,
        prereq_chain=prereq_chain,
    )