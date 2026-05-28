from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class JDAnalysis(BaseModel):
    stack: list[str]
    level: Literal["junior", "mid", "senior", "unknown"]
    suggested_domain: str
    key_topics: list[str]
    company_type: Literal["startup", "tech_startup", "enterprise", "agency", "unknown"]
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("level", "company_type", mode="before")
    @classmethod
    def normalize_to_lowercase(cls, v: Any) -> Any:
        return v.lower() if isinstance(v, str) else v
    # Generated once in create_session(); stored in sessions.jd_analysis JSON.
    # Used by few_shot prompt builder to produce domain-specific examples.
    few_shot_examples: list[str] = Field(default_factory=list)
