import textwrap
from typing import TypedDict

from apps.courses.models import Course


class CourseChunk(TypedDict):
    course_id: str
    text: str
    metadata: dict


def course_to_chunk(course: Course) -> CourseChunk:
    """Convert a Course model instance into a text chunk + metadata dict."""
    tags = ', '.join(t.name for t in course.tags.all())

    parts = [
        f"Title: {course.title}",
        f"Instructor: {course.instructor or 'N/A'}",
        f"Level: {course.level or 'N/A'}",
        f"Duration: {course.duration or 'N/A'}",
        f"Rating: {course.rating}/5 ({course.reviews_count} reviews)" if course.rating else "Rating: N/A",
        f"Price: {course.currency} {course.price}" if course.price else "Price: Free",
        f"Platform: {course.platform.name}",
        f"",
        f"Description: {course.description[:1000]}" if course.description else "",
        f"",
        f"What You'll Learn: {course.what_you_learn[:800]}" if course.what_you_learn else "",
        f"",
        f"Tags: {tags}" if tags else "",
    ]

    text = '\n'.join(parts)
    text = textwrap.fill(text, width=2000)

    metadata = {
        'course_id': str(course.id),
        'title': course.title,
        'instructor': course.instructor,
        'level': course.level,
        'duration': course.duration,
        'rating': float(course.rating) if course.rating else None,
        'reviews_count': course.reviews_count,
        'price': float(course.price) if course.price else None,
        'currency': course.currency,
        'platform': course.platform.name,
        'url': course.url,
        'thumbnail_url': course.thumbnail_url,
        'description': course.description[:500],
        'what_you_learn': course.what_you_learn[:300],
        'tags': tags,
        'video_hours': float(course.video_hours) if course.video_hours else None,
    }

    return CourseChunk(course_id=str(course.id), text=text, metadata=metadata)


def courses_to_chunks(courses) -> list[CourseChunk]:
    """Batch convert a queryset or list of Course instances."""
    return [course_to_chunk(c) for c in courses]
