from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class JDAnalysis(BaseModel):
    stack: list[str]
    level: Literal["junior", "mid", "senior", "unknown"]
    suggested_domain: str
    key_topics: list[str]
    company_type: Literal["startup", "tech_startup", "enterprise", "agency", "unknown"]
    confidence: float = Field(ge=0.0, le=1.0)
