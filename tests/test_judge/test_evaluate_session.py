"""Tests for LLM-as-a-judge evaluation pipeline."""

import json
from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from lib.prompts.judge import build_judge_context, derive_summary_from_detailed
from lib.schemas.judge import (
    CriterionScore,
    DetailedReport,
    SummaryReport,
)
from lib.schemas.messages import Message
from lib.schemas.session import Session

# ── Sample judge response payload ─────────────────────────────────

SAMPLE_JUDGE_RESPONSE = {
    "schema_version": "1.0",
    "format_type": "detailed",
    "session_id": "test-session-123",
    "session_metadata": {
        "domain": "backend",
        "difficulty": "medium",
        "interviewer_persona": "neutral",
        "prompt_technique": "role_playing",
        "llm_model": "openai/gpt-5-mini",
        "duration_seconds": 600,
        "total_messages": 6,
        "total_cost_eur_cents": 5,
    },
    "overall_assessment": {
        "overall_score": 7.5,
        "readiness_level": "ready",
        "scores_by_criterion": {
            "correctness": {"average": 7.0, "min": 6, "max": 8},
            "depth": {"average": 8.0, "min": 7, "max": 9},
            "structure": {"average": 7.5, "min": 7, "max": 8},
            "communication": {"average": 7.0, "min": 6, "max": 8},
        },
        "verdict": "Strong backend candidate with good async knowledge.",
    },
    "question_by_question": [
        {
            "sequence_number": 1,
            "question": "Tell me about async Python.",
            "user_answer": "I use asyncio and FastAPI.",
            "scores": {
                "correctness": 7,
                "depth": 8,
                "structure": 7,
                "communication": 7,
            },
            "reasoning": {
                "correctness": "Correct basics.",
                "depth": "Good depth.",
                "structure": "Well structured.",
                "communication": "Clear.",
            },
            "key_strengths": ["Good asyncio knowledge"],
            "areas_to_improve": ["Could mention event loop details"],
        }
    ],
    "strengths": [
        {
            "area": "Async programming",
            "evidence": "Mentioned asyncio correctly",
            "level": "moderate",
        }
    ],
    "weaknesses": [
        {
            "area": "System design",
            "evidence": "Did not mention distributed aspects",
            "level": "minor",
            "impact_on_role": "Limited",
        }
    ],
    "improvement_plan": [
        {
            "action": "Study distributed systems",
            "priority": "medium",
            "estimated_hours": 20,
            "resources": [
                {
                    "type": "book",
                    "title": "Designing Data-Intensive Applications",
                    "url": None,
                }
            ],
            "success_criterion": "Can explain CAP theorem and implement a distributed lock",
        }
    ],
    "interviewer_notes": "Promising candidate.",
}


def _make_session(session_id: str | None = None) -> Session:
    """Build a minimal Session for tests."""
    now = datetime.utcnow()
    return Session(
        id=uuid4() if session_id is None else session_id,  # type: ignore[arg-type]
        user_id=None,
        guest_token=None,
        guest_token_expires_at=None,
        status="completed",
        domain="backend",
        difficulty="medium",
        interviewer_persona="neutral",
        prompt_technique="role_playing",
        llm_model="openai/gpt-5-mini",
        temperature=0.7,
        top_p=1.0,
        max_tokens=1024,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        total_input_tokens=100,
        total_output_tokens=200,
        total_cost_usd_cents=5,
        share_token=None,
        share_enabled=False,
        created_at=now,
        updated_at=now,
        completed_at=now,
    )


def _make_message(role: str, content: str, seq: int) -> Message:
    return Message(
        id=uuid4(),
        session_id=uuid4(),
        role=role,  # type: ignore[arg-type]
        content=content,
        sequence_number=seq,
        input_tokens=None,
        output_tokens=None,
        cost_usd_cents=None,
        latency_ms=None,
        suspicious=False,
        metadata={},
        created_at=datetime.utcnow(),
    )


# ── Pydantic validation tests (no LLM calls) ──────────────────────


def test_detailed_report_validates() -> None:
    """DetailedReport Pydantic model should validate sample judge output."""
    report = DetailedReport.model_validate(SAMPLE_JUDGE_RESPONSE)
    assert report.overall_assessment.overall_score == 7.5
    assert report.overall_assessment.readiness_level == "ready"
    assert len(report.question_by_question) == 1
    assert report.session_id == "test-session-123"


def test_summary_report_validates() -> None:
    """SummaryReport should validate minimal correct structure."""
    summary_data = {
        "schema_version": "1.0",
        "format_type": "summary",
        "session_id": "test-123",
        "domain": "backend",
        "completed_at": "2026-05-21T12:00:00",
        "overall_score": 7.5,
        "readiness_level": "ready",
        "verdict": "Strong backend candidate with solid knowledge of async Python and database optimization techniques.",
        "top_strengths": ["Async programming", "SQL optimization"],
        "top_weaknesses": ["System design", "Distributed systems"],
        "next_actions": [
            {"action": "Study CAP theorem", "priority": "medium"},
            {"action": "Practice system design interviews", "priority": "high"},
        ],
    }
    report = SummaryReport.model_validate(summary_data)
    assert report.overall_score == 7.5


def test_overall_score_validation_rejects_above_10() -> None:
    """Score outside [1.0, 10.0] should fail validation."""
    invalid_data = dict(SAMPLE_JUDGE_RESPONSE)
    invalid_data["overall_assessment"] = {
        **SAMPLE_JUDGE_RESPONSE["overall_assessment"],
        "overall_score": 11.0,
    }
    with pytest.raises(ValidationError):
        DetailedReport.model_validate(invalid_data)


def test_overall_score_validation_rejects_below_1() -> None:
    """Score below 1.0 must fail validation."""
    invalid_data = dict(SAMPLE_JUDGE_RESPONSE)
    invalid_data["overall_assessment"] = {
        **SAMPLE_JUDGE_RESPONSE["overall_assessment"],
        "overall_score": 0.0,
    }
    with pytest.raises(ValidationError):
        DetailedReport.model_validate(invalid_data)


def test_criterion_score_average() -> None:
    """CriterionScore.average property should compute mean of 4 criteria."""
    score = CriterionScore(correctness=8, depth=6, structure=7, communication=9)
    assert score.average == pytest.approx(7.5)


def test_detailed_report_session_metadata_roundtrips() -> None:
    """SessionMetadata must survive model_validate → model_dump → model_validate."""
    report = DetailedReport.model_validate(SAMPLE_JUDGE_RESPONSE)
    dumped = report.model_dump()
    report2 = DetailedReport.model_validate(dumped)
    assert report2.session_metadata.domain == "backend"
    assert report2.session_metadata.total_cost_eur_cents == 5


# ── build_judge_context ────────────────────────────────────────────


def test_build_judge_context_excludes_system_messages(
    sample_jd_analysis,
) -> None:
    """build_judge_context must skip system messages."""
    session = _make_session()
    messages = [
        _make_message("system", "You are an interviewer.", 0),
        _make_message("assistant", "Tell me about async Python.", 1),
        _make_message("user", "I use asyncio.", 2),
    ]
    context = build_judge_context(session, messages, sample_jd_analysis)
    assert "system" not in context.lower() or "You are an interviewer." not in context


def test_build_judge_context_labels_roles(sample_jd_analysis) -> None:
    """build_judge_context must use INTERVIEWER/CANDIDATE labels."""
    session = _make_session()
    messages = [
        _make_message("assistant", "How do you handle async?", 1),
        _make_message("user", "I use asyncio.", 2),
    ]
    context = build_judge_context(session, messages, sample_jd_analysis)
    assert "INTERVIEWER" in context
    assert "CANDIDATE" in context


def test_build_judge_context_returns_string(sample_jd_analysis) -> None:
    """build_judge_context must always return a string."""
    session = _make_session()
    result = build_judge_context(session, [], sample_jd_analysis)
    assert isinstance(result, str)


# ── derive_summary_from_detailed ──────────────────────────────────


def test_derive_summary_from_detailed_inherits_score() -> None:
    """derive_summary_from_detailed must copy overall_score from detailed."""
    detailed = DetailedReport.model_validate(SAMPLE_JUDGE_RESPONSE)
    summary = derive_summary_from_detailed(detailed, "test-session-123", "backend")
    assert summary.overall_score == detailed.overall_assessment.overall_score


def test_derive_summary_from_detailed_inherits_readiness() -> None:
    """derive_summary_from_detailed must copy readiness_level from detailed."""
    detailed = DetailedReport.model_validate(SAMPLE_JUDGE_RESPONSE)
    summary = derive_summary_from_detailed(detailed, "test-session-123", "backend")
    assert summary.readiness_level == detailed.overall_assessment.readiness_level


def test_derive_summary_from_detailed_returns_valid_model() -> None:
    """derive_summary_from_detailed must return a valid SummaryReport."""
    detailed = DetailedReport.model_validate(SAMPLE_JUDGE_RESPONSE)
    summary = derive_summary_from_detailed(detailed, "test-session-123", "backend")
    # Should not raise
    SummaryReport.model_validate(summary.model_dump())


# ── evaluate_session (LLM mocked) ────────────────────────────────


@pytest.mark.asyncio
async def test_evaluate_session_returns_tuple_on_success(
    mocker,
    sample_messages,
    sample_jd_analysis,
) -> None:
    """evaluate_session must return (SummaryReport, DetailedReport) on success."""
    mocker.patch(
        "lib.prompts.judge.chat_complete",
        return_value={
            "choices": [{"message": {"content": json.dumps(SAMPLE_JUDGE_RESPONSE)}}],
            "usage": {"prompt_tokens": 800, "completion_tokens": 400},
        },
    )
    mocker.patch(
        "lib.prompts.judge.get_message_content",
        return_value=json.dumps(SAMPLE_JUDGE_RESPONSE),
    )

    from lib.prompts.judge import evaluate_session

    session = _make_session()
    summary, detailed = await evaluate_session(session, sample_messages, sample_jd_analysis)

    assert isinstance(summary, SummaryReport)
    assert isinstance(detailed, DetailedReport)


@pytest.mark.asyncio
async def test_evaluate_session_falls_back_on_llm_failure(
    mocker,
    sample_messages,
    sample_jd_analysis,
) -> None:
    """evaluate_session must return degraded reports when LLM fails twice."""
    mocker.patch(
        "lib.prompts.judge.chat_complete",
        side_effect=Exception("LLM unavailable"),
    )

    from lib.prompts.judge import evaluate_session

    session = _make_session()
    summary, detailed = await evaluate_session(session, sample_messages, sample_jd_analysis)

    # Degraded reports must still be valid Pydantic models
    assert isinstance(summary, SummaryReport)
    assert isinstance(detailed, DetailedReport)
    # Degraded scores are set to 5.0
    assert detailed.overall_assessment.overall_score == 5.0
