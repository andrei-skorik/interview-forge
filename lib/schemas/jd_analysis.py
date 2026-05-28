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

    @field_validator("level", mode="before")
    @classmethod
    def normalize_level(cls, v: Any) -> str:
        if not isinstance(v, str):
            return "unknown"
        v = v.lower()
        if v in ("junior", "mid", "senior", "unknown"):
            return v
        if "senior" in v or "lead" in v or "principal" in v or "staff" in v:
            return "senior"
        if "junior" in v or "entry" in v or "graduate" in v:
            return "junior"
        if "mid" in v or "middle" in v or "medior" in v:
            return "mid"
        return "unknown"

    @field_validator("company_type", mode="before")
    @classmethod
    def normalize_company_type(cls, v: Any) -> str:
        if not isinstance(v, str):
            return "unknown"
        v = v.lower()
        if v in ("startup", "tech_startup", "enterprise", "agency", "unknown"):
            return v
        return "unknown"
    # Generated once in create_session(); stored in sessions.jd_analysis JSON.
    # Used by few_shot prompt builder to produce domain-specific examples.
    few_shot_examples: list[str] = Field(default_factory=list)
