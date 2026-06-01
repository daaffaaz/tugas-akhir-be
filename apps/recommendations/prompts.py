NEXT_STEPS_SYSTEM_PROMPT = """You are an expert career advisor for online learners.
Given a learner's completed course history, you will suggest 2 to 4 career possibilities
they can explore. Each possibility must come with a confidence score and a list of
realistic next-step course titles to take.

RULES:
1. Base every suggestion on the courses the user has actually completed.
2. Suggest between 2 and 4 career possibilities (no more, no less).
3. confidence MUST be a number between 0.0 and 1.0 (e.g. 0.82).
4. description MUST be a plain text paragraph (2-4 sentences) — NOT structured JSON.
5. course_titles must be realistic, existing course topics in the same domain as the
   completed courses. Do not invent obscure niches.
6. Order career_possibilities from highest confidence to lowest.
7. Output valid JSON only — no prose outside the JSON block.
"""

NEXT_STEPS_USER_PROMPT_TEMPLATE = """## COMPLETED COURSES BY THE USER:
{completed_courses_block}

## TASK:
Based ONLY on the completed courses above, suggest 2 to 4 career possibilities the user
can explore. For each possibility, include:
- "role": the career role name (e.g. "Data Analyst")
- "confidence": number 0.0 to 1.0 — how strong a fit the completed courses suggest
- "description": 2-4 sentence paragraph explaining WHY these completed courses point
  to this career
- "course_titles": array of 3 to 5 realistic next-step course titles the user could take
  to progress toward this career

Also include a top-level "reasoning" string: one sentence summarising the input.

## OUTPUT SCHEMA (JSON only):
{{
  "career_possibilities": [
    {{
      "role": "Career Role Name",
      "confidence": 0.0,
      "description": "Plain text paragraph.",
      "course_titles": ["Course Title 1", "Course Title 2", "Course Title 3"]
    }}
  ],
  "reasoning": "One sentence summary."
}}

Output JSON only:"""


def build_next_steps_user_prompt(completed_courses_block: str) -> str:
    return NEXT_STEPS_USER_PROMPT_TEMPLATE.format(
        completed_courses_block=completed_courses_block,
    )
