from pydantic import BaseModel, Field


class RoadmapCourse(BaseModel):
    course_id: str = Field(description="UUID of the course from the database")
    title: str
    match_reason: str
    focus_areas: list[str] = Field(default_factory=list)
    estimated_hours: float | None = None


class SkillProgress(BaseModel):
    skills_gained: list[str] = Field(default_factory=list)
    skill_coverage: float = Field(ge=0, le=1)


class RoadmapPhase(BaseModel):
    phase_number: int = Field(ge=1)
    phase_name: str
    duration_weeks: int = Field(ge=1)
    learning_objectives: list[str] = Field(default_factory=list)
    courses: list[RoadmapCourse]
    milestones: list[str] = Field(default_factory=list)
    practice_projects: list[str] = Field(default_factory=list)
    skill_progress: SkillProgress = Field(default_factory=SkillProgress)


class RoadmapOutput(BaseModel):
    roadmap_id: str | None = None
    generated_at: str | None = None
    roadmap_title: str
    target_skills: list[str]
    total_duration_weeks: int
    total_hours_estimated: int
    difficulty_curve: str
    overview: str
    phases: list[RoadmapPhase]
    cross_phase_learning: list[str] = Field(default_factory=list)
    tips_for_success: list[str] = Field(default_factory=list)
    next_steps_after_roadmap: list[str] = Field(default_factory=list)
    validation: dict = Field(default_factory=dict)
