from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from lib.schemas.jd_analysis import JDAnalysis
    from lib.schemas.messages import Message


class SessionConfig(BaseModel):
    job_description: str = Field(min_length=50, max_length=10_000)
    domain: Literal["frontend", "backend", "data_ml", "devops", "system_design", "behavioral"]
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    response_length: Literal["concise", "detailed"] = "detailed"
    interviewer_persona: Literal["strict", "neutral", "friendly"] = "neutral"
    prompt_technique: Literal[
        "zero_shot", "few_shot", "chain_of_thought", "role_playing", "structured_output"
    ] = "role_playing"
    llm_model: Literal["openai/gpt-5-mini", "openai/gpt-5-nano"] = "openai/gpt-5-mini"
    temperature: float = Field(0.7, ge=0.0, le=1.5)
    top_p: float = Field(1.0, ge=0.0, le=1.0)
    max_tokens: int = Field(1024, ge=256, le=4096)
    frequency_penalty: float = Field(0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(0.0, ge=-2.0, le=2.0)


class Session(BaseModel):
    id: UUID
    user_id: UUID | None
    guest_token: str | None
    guest_token_expires_at: datetime | None
    status: Literal["in_progress", "evaluating", "completed", "completed_without_eval", "abandoned"]
    domain: str
    difficulty: str
    interviewer_persona: str
    prompt_technique: str
    llm_model: str
    temperature: float
    top_p: float
    max_tokens: int
    frequency_penalty: float
    presence_penalty: float
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd_cents: int
    share_token: str | None
    share_enabled: bool
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class SessionCost(BaseModel):
    session_total_usd_cents: int
    session_total_eur_cents: int
    last_message_usd_cents: int
    last_message_eur_cents: int


class SessionReportPreview(BaseModel):
    session_id: UUID
    overall_score: float
    readiness_level: str


class GuestSessionRef(BaseModel):
    session_id: str
    guest_token: str


class SessionFilters(BaseModel):
    domains: list[str]
    status: str | None
    date_from: datetime | None
    date_to: datetime | None


class SessionsList(BaseModel):
    sessions: list[Session]
    total: int
    page: int
    per_page: int


class SessionWithMessages(Session):
    messages: list[Message] = Field(default_factory=list)
    evaluations: list[object] = Field(default_factory=list)


class CreateSessionResult(BaseModel):
    session: Session
    jd_analysis: JDAnalysis
    first_message: Message
    cost: SessionCost


class FinishResult(BaseModel):
    session_id: UUID
    status: Literal["completed", "completed_without_eval"]
    report: SessionReportPreview
    evaluations_count: int
    total_cost_usd_cents: int
    total_cost_eur_cents: int
    evaluation_time_ms: int


class DeleteResult(BaseModel):
    deleted: bool
    sessions_deleted: int
    embeddings_deleted: int
    anonymized_user_id: str


def _rebuild_models() -> None:
    from lib.schemas.jd_analysis import JDAnalysis  # noqa: PLC0415
    from lib.schemas.messages import Message  # noqa: PLC0415

    ns = {"JDAnalysis": JDAnalysis, "Message": Message}
    SessionWithMessages.model_rebuild(_types_namespace=ns)
    CreateSessionResult.model_rebuild(_types_namespace=ns)


_rebuild_models()
