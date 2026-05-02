SYSTEM_PROMPT = """You are an expert learning path advisor for online micro-credentials and courses.
You MUST only recommend courses that exist in the provided context.
Do NOT invent course names, URLs, instructor names, or details.
If no suitable course exists for a topic, say "No matching course available."

ROADMAP GENERATION RULES:
1. Analyze the user's current skill level and goals from their profile.
2. Design a phase-by-phase roadmap that respects the prerequisite ordering shown.
3. For EACH phase, recommend ONLY courses from the AVAILABLE COURSES list.
4. Include exact course_id (UUID format) for every recommended course.
5. Estimate realistic duration: course video_hours + 20% practice time.
6. Keep each phase to 2-5 courses maximum for realistic workload.
7. Output valid JSON only — no explanatory text outside the JSON block.
8. Respect budget and level constraints if specified.
9. Always include at least 1 course per phase if available courses allow it.
"""

USER_PROMPT_TEMPLATE = """## USER PROFILE:
{user_profile}

## TOPIC REQUESTED:
{topic}

## AVAILABLE COURSES (retrieved from database):
{courses_context}

## PREREQUISITE CHAIN (suggested learning order):
{prereq_chain}

## OUTPUT SCHEMA:
{{
  "roadmap_title": "Descriptive title for this roadmap",
  "target_skills": ["list of skills the user will gain"],
  "total_duration_weeks": total number of weeks across all phases,
  "total_hours_estimated": total estimated learning hours,
  "difficulty_curve": "beginner-friendly / progressive / intensive",
  "overview": "1-2 paragraph overview of the entire roadmap",
  "phases": [
    {{
      "phase_number": 1,
      "phase_name": "Phase name",
      "duration_weeks": 2,
      "learning_objectives": ["objective 1", "objective 2"],
      "courses": [
        {{
          "course_id": "UUID from AVAILABLE COURSES list above",
          "title": "exact title from AVAILABLE COURSES",
          "match_reason": "why this course was chosen",
          "focus_areas": ["topic areas to focus on"],
          "estimated_hours": float
        }}
      ],
      "milestones": ["milestone 1", "milestone 2"],
      "practice_projects": ["project idea 1"],
      "skill_progress": {{
        "skills_gained": ["skill 1"],
        "skill_coverage": 0.0-1.0
      }}
    }}
  ],
  "cross_phase_learning": ["skill developed across all phases"],
  "tips_for_success": ["tip 1", "tip 2"],
  "next_steps_after_roadmap": ["what to do after completing"],
  "retrieval_info": {{
    "courses_retrieved": number,
    "top_similarity_score": float,
    "retrieval_method": "semantic vector search"
  }},
  "validation": {{
    "all_courses_valid": true/false,
    "prerequisites_respected": true/false,
    "no_hallucinated_courses": true/false
  }}
}}

Output JSON only:"""


def build_user_prompt(topic, user_profile, courses_context, prereq_chain):
    return USER_PROMPT_TEMPLATE.format(
        user_profile=user_profile,
        topic=topic,
        courses_context=courses_context,
        prereq_chain=prereq_chain,
    )
