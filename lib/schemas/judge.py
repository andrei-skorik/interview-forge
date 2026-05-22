from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class NextAction(BaseModel):
    action: str
    priority: Literal["high", "medium", "low"]


class SummaryReport(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    format_type: Literal["summary"] = "summary"
    session_id: str
    domain: str
    completed_at: str
    overall_score: float = Field(ge=1.0, le=10.0)
    readiness_level: Literal["not_ready", "needs_practice", "ready", "strong_candidate"]
    verdict: str = Field(min_length=50, max_length=500)
    top_strengths: list[str] = Field(min_length=2, max_length=5)
    top_weaknesses: list[str] = Field(min_length=2, max_length=5)
    next_actions: list[NextAction] = Field(min_length=2, max_length=5)


class CriterionScore(BaseModel):
    correctness: int = Field(ge=1, le=10)
    depth: int = Field(ge=1, le=10)
    structure: int = Field(ge=1, le=10)
    communication: int = Field(ge=1, le=10)

    @property
    def average(self) -> float:
        return (self.correctness + self.depth + self.structure + self.communication) / 4


class CriterionReasoning(BaseModel):
    correctness: str
    depth: str
    structure: str
    communication: str


class QuestionEvaluation(BaseModel):
    sequence_number: int
    question: str
    user_answer: str
    scores: CriterionScore
    reasoning: CriterionReasoning
    key_strengths: list[str]
    areas_to_improve: list[str]


class Resource(BaseModel):
    type: Literal["course", "book", "article", "paper", "video", "practice"]
    title: str
    url: str | None = None


class ImprovementAction(BaseModel):
    action: str
    priority: Literal["high", "medium", "low"]
    estimated_hours: int = Field(ge=1, le=100)
    resources: list[Resource]
    success_criterion: str


class StrengthArea(BaseModel):
    area: str
    evidence: str
    level: Literal["emerging", "moderate", "strong"]


class WeaknessArea(BaseModel):
    area: str
    evidence: str
    level: Literal["minor", "moderate", "significant"]
    impact_on_role: str


class ScoresByCriterion(BaseModel):
    average: float
    min: int
    max: int


class OverallAssessment(BaseModel):
    overall_score: float = Field(ge=1.0, le=10.0)
    readiness_level: Literal["not_ready", "needs_practice", "ready", "strong_candidate"]
    scores_by_criterion: dict[str, ScoresByCriterion]
    verdict: str


class SessionMetadata(BaseModel):
    domain: str
    difficulty: str
    interviewer_persona: str
    prompt_technique: str
    llm_model: str
    duration_seconds: int
    total_messages: int
    total_cost_eur_cents: int


class DetailedReport(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    format_type: Literal["detailed"] = "detailed"
    session_id: str
    session_metadata: SessionMetadata
    overall_assessment: OverallAssessment
    question_by_question: list[QuestionEvaluation]
    strengths: list[StrengthArea]
    weaknesses: list[WeaknessArea]
    improvement_plan: list[ImprovementAction]
    interviewer_notes: str
