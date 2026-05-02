from pydantic import BaseModel, Field


class RoadmapCourse(BaseModel):
    course_id: str = Field(description="UUID of the course from the database")
    title: str
    match_reason: str = Field(description="Why this course was selected for this phase")
    focus_areas: list[str] = Field(default_factory=list)
    estimated_hours: float | None = None


class SkillProgress(BaseModel):
    skills_gained: list[str] = Field(default_factory=list)
    skill_coverage: float = Field(ge=0, le=1, description="0-1 coverage ratio")


class RoadmapPhase(BaseModel):
    phase_number: int = Field(ge=1)
    phase_name: str
    duration_weeks: int = Field(ge=1)
    learning_objectives: list[str] = Field(default_factory=list)
    courses: list[RoadmapCourse]
    milestones: list[str] = Field(default_factory=list)
    practice_projects: list[str] = Field(default_factory=list)
    skill_progress: SkillProgress = Field(default_factory=SkillProgress)


class RetrievalInfo(BaseModel):
    courses_retrieved: int
    top_similarity_score: float
    retrieval_method: str = "hybrid (semantic + tag-based ordering)"


class RoadmapOutput(BaseModel):
    roadmap_id: str | None = None
    generated_at: str | None = None
    retrieval_info: RetrievalInfo
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
