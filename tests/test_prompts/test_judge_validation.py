"""Tests for Pydantic schemas used by the LLM judge."""

import pytest
from pydantic import ValidationError

from lib.schemas.judge import (
    CriterionScore,
    DetailedReport,
    SummaryReport,
)

# ── Shared test data ───────────────────────────────────────────────

MINIMAL_OVERALL_ASSESSMENT = {
    "overall_score": 7.5,
    "readiness_level": "ready",
    "scores_by_criterion": {
        "correctness": {"average": 7.0, "min": 6, "max": 8},
        "depth": {"average": 8.0, "min": 7, "max": 9},
        "structure": {"average": 7.5, "min": 7, "max": 8},
        "communication": {"average": 7.0, "min": 6, "max": 8},
    },
    "verdict": "Strong backend candidate.",
}

MINIMAL_SESSION_METADATA = {
    "domain": "backend",
    "difficulty": "medium",
    "interviewer_persona": "neutral",
    "prompt_technique": "role_playing",
    "llm_model": "openai/gpt-5-mini",
    "duration_seconds": 600,
    "total_messages": 6,
    "total_cost_eur_cents": 5,
}

MINIMAL_QBQ = [
    {
        "sequence_number": 1,
        "question": "Tell me about async Python.",
        "user_answer": "I use asyncio and FastAPI.",
        "scores": {"correctness": 7, "depth": 8, "structure": 7, "communication": 7},
        "reasoning": {
            "correctness": "Correct basics.",
            "depth": "Good depth.",
            "structure": "Well structured.",
            "communication": "Clear.",
        },
        "key_strengths": ["Good asyncio knowledge"],
        "areas_to_improve": ["Could mention event loop details"],
    }
]

MINIMAL_DETAILED_REPORT = {
    "schema_version": "1.0",
    "format_type": "detailed",
    "session_id": "test-session-123",
    "session_metadata": MINIMAL_SESSION_METADATA,
    "overall_assessment": MINIMAL_OVERALL_ASSESSMENT,
    "question_by_question": MINIMAL_QBQ,
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
                {"type": "book", "title": "Designing Data-Intensive Applications", "url": None}
            ],
            "success_criterion": "Can explain CAP theorem",
        }
    ],
    "interviewer_notes": "Promising candidate.",
}

MINIMAL_SUMMARY_REPORT = {
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


# ── SummaryReport ─────────────────────────────────────────────────


def test_summary_report_validates_with_valid_data() -> None:
    """SummaryReport.model_validate() must succeed with well-formed data."""
    report = SummaryReport.model_validate(MINIMAL_SUMMARY_REPORT)
    assert report.overall_score == 7.5
    assert report.readiness_level == "ready"
    assert len(report.top_strengths) == 2
    assert len(report.next_actions) == 2


def test_summary_report_rejects_score_below_1() -> None:
    """SummaryReport must reject overall_score below 1.0."""
    data = {**MINIMAL_SUMMARY_REPORT, "overall_score": 0.5}
    with pytest.raises(ValidationError):
        SummaryReport.model_validate(data)


def test_summary_report_rejects_score_above_10() -> None:
    """SummaryReport must reject overall_score above 10.0."""
    data = {**MINIMAL_SUMMARY_REPORT, "overall_score": 11.0}
    with pytest.raises(ValidationError):
        SummaryReport.model_validate(data)


def test_summary_report_rejects_invalid_readiness_level() -> None:
    """SummaryReport must reject readiness_level outside the allowed literals."""
    data = {**MINIMAL_SUMMARY_REPORT, "readiness_level": "expert"}
    with pytest.raises(ValidationError):
        SummaryReport.model_validate(data)


def test_summary_report_accepts_all_readiness_levels() -> None:
    """SummaryReport must accept all four valid readiness_level literals."""
    for level in ("not_ready", "needs_practice", "ready", "strong_candidate"):
        data = {**MINIMAL_SUMMARY_REPORT, "readiness_level": level}
        report = SummaryReport.model_validate(data)
        assert report.readiness_level == level


def test_summary_report_rejects_short_verdict() -> None:
    """SummaryReport verdict must be at least 50 characters."""
    data = {**MINIMAL_SUMMARY_REPORT, "verdict": "Too short."}
    with pytest.raises(ValidationError):
        SummaryReport.model_validate(data)


def test_summary_report_rejects_too_few_strengths() -> None:
    """SummaryReport top_strengths must have at least 2 items."""
    data = {**MINIMAL_SUMMARY_REPORT, "top_strengths": ["Only one item"]}
    with pytest.raises(ValidationError):
        SummaryReport.model_validate(data)


def test_summary_report_rejects_too_few_weaknesses() -> None:
    """SummaryReport top_weaknesses must have at least 2 items."""
    data = {**MINIMAL_SUMMARY_REPORT, "top_weaknesses": ["Only one item"]}
    with pytest.raises(ValidationError):
        SummaryReport.model_validate(data)


# ── DetailedReport ────────────────────────────────────────────────


def test_detailed_report_validates_with_valid_data() -> None:
    """DetailedReport.model_validate() must succeed with well-formed data."""
    report = DetailedReport.model_validate(MINIMAL_DETAILED_REPORT)
    assert report.overall_assessment.overall_score == 7.5
    assert report.overall_assessment.readiness_level == "ready"
    assert len(report.question_by_question) == 1


def test_detailed_report_rejects_score_above_10() -> None:
    """DetailedReport must reject overall_score above 10.0."""
    bad_assessment = {**MINIMAL_OVERALL_ASSESSMENT, "overall_score": 11.0}
    data = {**MINIMAL_DETAILED_REPORT, "overall_assessment": bad_assessment}
    with pytest.raises(ValidationError):
        DetailedReport.model_validate(data)


def test_detailed_report_with_empty_question_by_question() -> None:
    """DetailedReport with empty question_by_question list should still validate."""
    data = {**MINIMAL_DETAILED_REPORT, "question_by_question": []}
    report = DetailedReport.model_validate(data)
    assert report.question_by_question == []


def test_detailed_report_session_metadata_fields() -> None:
    """DetailedReport session_metadata must contain all required fields."""
    report = DetailedReport.model_validate(MINIMAL_DETAILED_REPORT)
    assert report.session_metadata.domain == "backend"
    assert report.session_metadata.difficulty == "medium"
    assert report.session_metadata.total_cost_eur_cents == 5


# ── CriterionScore ────────────────────────────────────────────────


def test_criterion_score_average_computes_correctly() -> None:
    """CriterionScore.average must return the arithmetic mean of all four fields."""
    score = CriterionScore(correctness=8, depth=6, structure=7, communication=9)
    assert score.average == pytest.approx(7.5)


def test_criterion_score_average_all_same() -> None:
    """CriterionScore.average is correct when all scores are equal."""
    score = CriterionScore(correctness=5, depth=5, structure=5, communication=5)
    assert score.average == pytest.approx(5.0)


def test_criterion_score_rejects_out_of_range() -> None:
    """CriterionScore must reject scores outside [1, 10]."""
    with pytest.raises(ValidationError):
        CriterionScore(correctness=0, depth=5, structure=5, communication=5)
    with pytest.raises(ValidationError):
        CriterionScore(correctness=5, depth=11, structure=5, communication=5)


def test_criterion_score_boundary_values() -> None:
    """CriterionScore must accept boundary values 1 and 10."""
    score = CriterionScore(correctness=1, depth=10, structure=1, communication=10)
    assert score.average == pytest.approx(5.5)
