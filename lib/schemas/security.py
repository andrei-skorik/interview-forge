from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    is_injection: bool
    confidence: float = Field(ge=0.0, le=1.0)
    method: str
    reason: str


class SecurityEvent(BaseModel):
    id: UUID
    user_id: UUID | None
    session_id: UUID | None
    ip_hash: str | None
    event_type: Literal[
        "prompt_injection_blocked",
        "rate_limit_exceeded",
        "suspicious_input_flagged",
        "invalid_token",
        "jailbreak_attempt",
    ]
    severity: Literal["low", "medium", "high", "critical"]
    input_excerpt: str | None
    detection_method: str
    detection_confidence: float | None
    detection_reason: str | None
    blocked: bool
    metadata: dict[str, object]
    created_at: datetime
