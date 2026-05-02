from apps.rag import config


# Keywords that indicate beginner/foundation level
BEGINNER_KEYWORDS = [
    'fundamentals', 'introduction', 'basics', 'beginner',
    'getting started', 'essentials', 'overview', 'starter',
    'fundamental', 'intro', 'basic',
]

# Keywords that indicate intermediate level
INTERMEDIATE_KEYWORDS = [
    'intermediate', 'applied', 'practical', 'hands-on',
    'applied', 'building', 'developing', 'with',
]

# Keywords that indicate advanced level
ADVANCED_KEYWORDS = [
    'advanced', 'expert', 'master', 'professional',
    'specialization', 'capstone', 'senior', 'deep',
]


def _level_from_keywords(title: str, tags: str, level: str) -> int:
    """Return 0=beginner, 1=intermediate, 2=advanced based on keyword scan."""
    combined = (title + ' ' + tags).lower()

    if any(k in combined for k in ADVANCED_KEYWORDS):
        return 2
    if any(k in combined for k in INTERMEDIATE_KEYWORDS):
        return 1
    if any(k in combined for k in BEGINNER_KEYWORDS):
        return 0

    # Fallback to explicit level field
    level_lower = level.lower() if level else ''
    if 'beginner' in level_lower or 'easy' in level_lower:
        return 0
    if 'intermediate' in level_lower or 'medium' in level_lower:
        return 1
    if 'advanced' in level_lower or 'hard' in level_lower:
        return 2

    return 1  # default to intermediate


def build_prereq_chain(courses_metadata: list[dict]) -> str:
    """
    Given a list of retrieved course metadata dicts (from FAISS),
    sort them by learning order and return a formatted prerequisite chain string.
    """
    if not courses_metadata:
        return "No courses retrieved."

    # Add sort key
    sorted_courses = sorted(
        courses_metadata,
        key=lambda c: _level_from_keywords(
            c.get('title', ''), c.get('tags', ''), c.get('level', '')
        )
    )

    # Build readable chain
    lines = []
    current_level = None
    for i, course in enumerate(sorted_courses, 1):
        level = _level_from_keywords(
            course.get('title', ''), course.get('tags', ''), course.get('level', '')
        )
        level_label = ['Foundation', 'Intermediate', 'Advanced'][level]

        if level != current_level:
            lines.append(f"\n[{level_label} Level]")
            current_level = level

        title = course.get('title', 'Unknown')[:70]
        duration = course.get('duration', 'N/A')
        lines.append(f"  {i}. {title} ({duration})")

    return '\n'.join(lines)


def get_skill_gap(target_topic: str, course_tags: list[str]) -> list[str]:
    """
    Simple heuristic: return tags that don't match the target topic.
    In production this would use a proper skill taxonomy.
    """
    topic_lower = target_topic.lower()
    related = [tag for tag in course_tags if topic_lower in tag.lower()]
    gaps = [tag for tag in course_tags if topic_lower not in tag.lower()]
    return gaps[:5]  # top 5 gaps