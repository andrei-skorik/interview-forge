from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from pydantic import BaseModel

if TYPE_CHECKING:
    from lib.schemas.session import SessionCost


class Message(BaseModel):
    id: UUID
    session_id: UUID
    role: Literal["user", "assistant", "system"]
    content: str
    sequence_number: int
    input_tokens: int | None
    output_tokens: int | None
    cost_usd_cents: int | None
    latency_ms: int | None
    suspicious: bool
    metadata: dict[str, object]
    created_at: datetime


class SimilarQuestion(BaseModel):
    id: UUID
    question_text: str
    similarity: float


class SendMessageResult(BaseModel):
    user_message: Message
    assistant_message: Message
    cost: SessionCost
    similar_questions_avoided: list[SimilarQuestion]


def _rebuild_models() -> None:
    from lib.schemas.session import SessionCost  # noqa: PLC0415

    SendMessageResult.model_rebuild(_types_namespace={"SessionCost": SessionCost})


_rebuild_models()
