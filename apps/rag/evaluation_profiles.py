"""
Persona templates for LLM-as-Judge evaluation.

Each persona mirrors the structure of a real production user profile
(as built by _build_user_profile() in views.py), ensuring the RAG system
receives realistic context during evaluation.

Profiles are auto-assigned by test case index via get_test_profile().
"""

from __future__ import annotations

from typing import Any

# Map of test case index → persona index.
# Designed so that each persona is used at least once across all 15 queries.
QUERY_PERSONA_MAP: dict[int, int] = {
    # Beginner personas (0) — broad, general queries
    0: 0,   # Web Development
    1: 0,   # Programming Languages
    12: 0,  # AI literacy

    # Hobbyist / casual learners (1)
    8: 1,   # SQL
    3: 1,   # Python
    14: 1,  # mobile app

    # Career changer / upskilling (2) — intermediate
    2: 2,   # Data Science
    7: 2,   # Data Analysis

    # Advanced professionals (3) — deep technical
    4: 3,   # Model Training
    5: 3,   # Machine Learning
    9: 3,   # Artificial Intelligence
    10: 3,  # Large Language Modeling

    # Professional / structured (4) — serious career focus
    6: 4,   # Software Testing
    13: 4,  # cloud aws

    # Expert / architecture (5) — advanced + senior
    11: 5,  # JavaScript
}

# Personas keyed by index. Each mirrors production profile fields from
# apps/rag/views.py:_build_user_profile() lines 111-201.
PERSONAS: list[dict[str, Any]] = [
    {
        "name": "beginner_general",
        "current_skills": [],
        "goals": [],
        "level": "Beginner",
        "budget": "<500k",
        "weekly_hours": "<4",
        "material_format": "video",
        "theory_practice": "theory",
        "main_goal": "hobby",
        "certification_importance": "",
        "additional_context": "",
    },
    {
        "name": "hobbyist_casual",
        "current_skills": ["Basic computer skills"],
        "goals": ["Web Development", "Python Programming"],
        "level": "Beginner",
        "budget": "500k-2m",
        "weekly_hours": "4-8",
        "material_format": "video",
        "theory_practice": "balanced",
        "main_goal": "hobby",
        "certification_importance": "",
        "additional_context": "Complete beginner exploring technology as a hobby.",
    },
    {
        "name": "career_changer",
        "current_skills": ["Microsoft Office", "Basic analytics"],
        "goals": ["Data Analysis", "SQL", "Data Science"],
        "level": "Beginner",
        "budget": "500k-2m",
        "weekly_hours": "8-14",
        "material_format": "project",
        "theory_practice": "practice",
        "main_goal": "career_change",
        "certification_importance": "high",
        "additional_context": "Non-technical professional transitioning to data roles.",
    },
    {
        "name": "advanced_engineer",
        "current_skills": ["Python", "Django", "PostgreSQL", "REST APIs"],
        "goals": ["Machine Learning", "Deep Learning", "AI Systems"],
        "level": "Advanced",
        "budget": ">2m",
        "weekly_hours": "15+",
        "material_format": "text",
        "theory_practice": "balanced",
        "main_goal": "upskilling",
        "certification_importance": "medium",
        "additional_context": "Experienced backend developer specializing in ML/AI systems.",
    },
    {
        "name": "professional_qa",
        "current_skills": ["Selenium", "Cypress", "Manual testing"],
        "goals": ["Automated Testing", "CI/CD", "DevOps"],
        "level": "Intermediate",
        "budget": "500k-2m",
        "weekly_hours": "6-10",
        "material_format": "project",
        "theory_practice": "practice",
        "main_goal": "career_change",
        "certification_importance": "high",
        "additional_context": "QA tester with manual testing experience seeking automation skills.",
    },
    {
        "name": "senior_fullstack",
        "current_skills": ["JavaScript", "React", "Node.js", "TypeScript"],
        "goals": ["Advanced Web Architecture", "Mobile Development", "System Design"],
        "level": "Advanced",
        "budget": ">2m",
        "weekly_hours": "10-14",
        "material_format": "text",
        "theory_practice": "balanced",
        "main_goal": "upskilling",
        "certification_importance": "",
        "additional_context": "Senior fullstack developer targeting mobile + architecture roles.",
    },
]


def get_test_profile(test_case_index: int) -> dict[str, Any]:
    """
    Return a realistic user profile dict for the given test case index.

    Each persona maps to a production-style profile with populated fields:
    current_skills, goals, level, budget, weekly_hours, material_format,
    theory_practice, main_goal, certification_importance, additional_context.

    Args:
        test_case_index: index of the test case within test_queries.json

    Returns:
        dict matching the structure used by _build_user_profile() in views.py
    """
    persona_idx = QUERY_PERSONA_MAP.get(test_case_index, 0)
    return dict(PERSONAS[persona_idx])
