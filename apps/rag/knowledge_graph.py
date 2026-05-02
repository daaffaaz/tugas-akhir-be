BEGINNER_KEYWORDS = [
    'fundamentals', 'introduction', 'basics', 'beginner',
    'getting started', 'essentials', 'overview', 'starter',
    'fundamental', 'intro', 'basic',
]
INTERMEDIATE_KEYWORDS = [
    'intermediate', 'applied', 'practical', 'hands-on',
    'building', 'developing', 'with',
]
ADVANCED_KEYWORDS = [
    'advanced', 'expert', 'master', 'professional',
    'specialization', 'capstone', 'senior', 'deep',
]


def _level_from_keywords(title: str, tags: str, level: str) -> int:
    combined = (title + ' ' + tags).lower()
    if any(k in combined for k in ADVANCED_KEYWORDS):
        return 2
    if any(k in combined for k in INTERMEDIATE_KEYWORDS):
        return 1
    if any(k in combined for k in BEGINNER_KEYWORDS):
        return 0
    level_lower = level.lower() if level else ''
    if 'beginner' in level_lower or 'easy' in level_lower:
        return 0
    if 'intermediate' in level_lower or 'medium' in level_lower:
        return 1
    if 'advanced' in level_lower or 'hard' in level_lower:
        return 2
    return 1


def build_prereq_chain(courses_metadata: list[dict]) -> str:
    """Sort courses by learning order and return formatted prerequisite chain."""
    if not courses_metadata:
        return "No courses retrieved."

    sorted_courses = sorted(
        courses_metadata,
        key=lambda c: _level_from_keywords(
            c.get('title', ''), c.get('tags', ''), c.get('level', '')
        )
    )

    lines = []
    current_level = None
    level_labels = ['Foundation', 'Intermediate', 'Advanced']

    for i, course in enumerate(sorted_courses, 1):
        level = _level_from_keywords(
            course.get('title', ''), course.get('tags', ''), course.get('level', '')
        )
        if level != current_level:
            lines.append(f"\n[{level_labels[level]} Level]")
            current_level = level

        title = course.get('title', 'Unknown')[:70]
        duration = course.get('duration', 'N/A')
        lines.append(f"  {i}. {title} ({duration})")

    return '\n'.join(lines)
