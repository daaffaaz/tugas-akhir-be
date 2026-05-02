import textwrap

from apps.rag import config, knowledge_graph, prompts


def course_to_text(course_meta: dict) -> str:
    """Format a single course metadata dict as a readable block for the prompt."""
    hours = course_meta.get('video_hours')
    duration = course_meta.get('duration', 'N/A')
    tags = course_meta.get('tags', '')

    lines = [
        f"— {course_meta.get('title', 'Unknown')} [ID: {course_meta.get('course_id', '')}]",
        f"  Instructor: {course_meta.get('instructor', 'N/A')} | Level: {course_meta.get('level', 'N/A')}",
        f"  Duration: {duration} | Hours: {hours or 'N/A'}h | Rating: {course_meta.get('rating', 'N/A')}/5",
        f"  Price: {course_meta.get('currency', 'IDR')} {course_meta.get('price', 'Free')}",
        f"  Tags: {tags}" if tags else "",
    ]
    desc = course_meta.get('description', '')
    if desc:
        lines.append(f"  Description: {textwrap.shorten(desc, width=300, placeholder='...')}")
    learn = course_meta.get('what_you_learn', '')
    if learn:
        lines.append(f"  What You'll Learn: {textwrap.shorten(learn, width=200, placeholder='...')}")
    return '\n'.join(l for l in lines if l)


def courses_to_context(courses_metadata: list[dict]) -> str:
    """Format top courses into a readable context block."""
    max_courses = config.RAG_MAX_CONTEXT_COURSES
    selected = courses_metadata[:max_courses]
    header = f"[AVAILABLE COURSES — {len(selected)} courses]\n"
    blocks = [course_to_text(c) for c in selected]
    return header + '\n\n'.join(blocks)


def build_retrieval_info(courses_retrieved: int, top_score: float) -> dict:
    return {
        'courses_retrieved': courses_retrieved,
        'top_similarity_score': round(top_score, 3),
        'retrieval_method': 'semantic vector search + tag-based ordering',
    }


def build_user_profile_text(topic, current_skills, goals, level, budget, weekly_hours) -> str:
    lines = [
        f"Topic/Goal: {topic}",
        f"Current Skills: {', '.join(current_skills) if current_skills else 'None specified'}",
        f"Target Skills: {', '.join(goals) if goals else 'Not specified'}",
        f"Preferred Level: {level or 'Any'}",
        f"Weekly Study Hours: {weekly_hours or 'Not specified'}",
        f"Budget: {'IDR {:,}'.format(budget) if budget else 'No limit'}",
    ]
    return '\n'.join(lines)


def assemble_prompt(topic: str, user_profile: dict, courses_metadata: list[dict], top_score: float) -> str:
    """Full prompt assembly. Returns the fully assembled user prompt string."""
    profile_text = build_user_profile_text(
        topic=topic,
        current_skills=user_profile.get('current_skills', []),
        goals=user_profile.get('goals', []),
        level=user_profile.get('level', ''),
        budget=user_profile.get('budget', None),
        weekly_hours=user_profile.get('weekly_hours', None),
    )
    courses_context = courses_to_context(courses_metadata)
    prereq_chain = knowledge_graph.build_prereq_chain(courses_metadata)

    return prompts.build_user_prompt(
        topic=topic,
        user_profile=profile_text,
        courses_context=courses_context,
        prereq_chain=prereq_chain,
    )
