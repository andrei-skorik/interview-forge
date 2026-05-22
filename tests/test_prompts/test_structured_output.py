"""Tests for structured-output prompt technique."""

import pytest
from pydantic import ValidationError

from lib.prompts.interviewer.structured_output import (
    InterviewerStructuredResponse,
    build_structured_output_prompt,
)
from lib.schemas.jd_analysis import JDAnalysis
from lib.schemas.session import SessionConfig


def test_returns_non_empty_string(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """build_structured_output_prompt must return a non-empty string."""
    result = build_structured_output_prompt(sample_session_config, sample_jd_analysis)
    assert isinstance(result, str)
    assert len(result) > 0


def test_prompt_contains_json_schema_instructions(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Prompt must instruct the model to produce valid JSON."""
    result = build_structured_output_prompt(sample_session_config, sample_jd_analysis)
    assert "json" in result.lower() or "JSON" in result


def test_prompt_contains_schema_fields(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Prompt must embed the Pydantic schema (field names visible)."""
    result = build_structured_output_prompt(sample_session_config, sample_jd_analysis)
    assert "question" in result
    assert "internal_notes" in result


def test_prompt_contains_domain_and_difficulty(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Prompt must reference domain and difficulty from config."""
    result = build_structured_output_prompt(sample_session_config, sample_jd_analysis)
    assert sample_session_config.domain in result
    assert sample_session_config.difficulty in result


def test_interviewer_structured_response_is_pydantic_model() -> None:
    """InterviewerStructuredResponse must be a valid Pydantic BaseModel."""
    from pydantic import BaseModel

    assert issubclass(InterviewerStructuredResponse, BaseModel)


def test_interviewer_structured_response_validates_sample_output() -> None:
    """InterviewerStructuredResponse must validate a well-formed sample payload."""
    data = {
        "question_type": "conceptual",
        "topic": "async programming",
        "question": "Explain the Python event loop.",
        "expected_depth": "intermediate",
        "hints_available": ["Think about coroutines", "Consider asyncio.run()"],
        "internal_notes": "Expect candidate to mention coroutines and event loop scheduling.",
    }
    model = InterviewerStructuredResponse.model_validate(data)
    assert model.question == "Explain the Python event loop."
    assert model.question_type == "conceptual"
    assert model.expected_depth == "intermediate"
    assert len(model.hints_available) == 2


def test_interviewer_structured_response_rejects_invalid_question_type() -> None:
    """InterviewerStructuredResponse must reject invalid question_type literal."""
    data = {
        "question_type": "unknown_type",
        "topic": "async",
        "question": "How does async work?",
        "expected_depth": "surface",
        "hints_available": [],
        "internal_notes": "",
    }
    with pytest.raises(ValidationError):
        InterviewerStructuredResponse.model_validate(data)


def test_interviewer_structured_response_rejects_invalid_depth() -> None:
    """InterviewerStructuredResponse must reject invalid expected_depth literal."""
    data = {
        "question_type": "scenario",
        "topic": "databases",
        "question": "How would you shard a Postgres database?",
        "expected_depth": "expert",  # invalid
        "hints_available": [],
        "internal_notes": "Notes here.",
    }
    with pytest.raises(ValidationError):
        InterviewerStructuredResponse.model_validate(data)


def test_prompt_contains_key_topics(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Prompt must reference at least one key topic from jd_analysis."""
    result = build_structured_output_prompt(sample_session_config, sample_jd_analysis)
    assert any(topic in result for topic in sample_jd_analysis.key_topics)
