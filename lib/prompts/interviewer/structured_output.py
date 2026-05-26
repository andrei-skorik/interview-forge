from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel

from lib.schemas.jd_analysis import JDAnalysis
from lib.schemas.session import SessionConfig


class InterviewerStructuredResponse(BaseModel):
    question_type: Literal["conceptual", "scenario", "follow_up", "deep_dive"]
    topic: str
    question: str
    expected_depth: Literal["surface", "intermediate", "deep"]
    hints_available: list[str]
    internal_notes: str


def _jd_excerpt(job_description: str, max_chars: int = 700) -> str:
    text = job_description.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + " …"


def build_structured_output_prompt(config: SessionConfig, jd_analysis: JDAnalysis) -> str:
    topics_str = (
        ", ".join(jd_analysis.key_topics) if jd_analysis.key_topics else "core competencies"
    )
    jd_text = _jd_excerpt(config.job_description)
    schema = InterviewerStructuredResponse.model_json_schema()
    schema_str = json.dumps(schema, indent=2)
    return f"""You are a technical interviewer. Respond with valid JSON only, matching this schema:

{schema_str}

The "internal_notes" field is NOT shown to the candidate — it's for your reference only.
The "question" field is what you ask the candidate.
The "hints_available" are hints you can give if the candidate struggles (keep them to yourself unless needed).

Difficulty: {config.difficulty}
JD topics: {topics_str}

--- JOB POSTING ---
{jd_text}
--- END ---

Base your questions on the actual role described in the job posting above."""
