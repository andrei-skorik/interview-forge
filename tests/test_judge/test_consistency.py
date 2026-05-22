"""Tests for judge score determinism — same input always gives same computed fields."""

import pytest

from lib.schemas.judge import CriterionScore, DetailedReport, SummaryReport


def test_criterion_score_average_is_deterministic() -> None:
    """CriterionScore.average must return the same value for identical inputs."""
    score = CriterionScore(correctness=8, depth=6, structure=7, communication=9)
    assert score.average == score.average  # computed property, same each time
    assert score.average == pytest.approx(7.5)


def test_criterion_score_all_same() -> None:
    for value in range(1, 11):
        score = CriterionScore(correctness=value, depth=value, structure=value, communication=value)
        assert score.average == pytest.approx(float(value))


def test_detailed_report_overall_score_stable(sample_detailed_report: dict) -> None:
    """Same DetailedReport dict always produces the same overall_score."""
    r1 = DetailedReport.model_validate(sample_detailed_report)
    r2 = DetailedReport.model_validate(sample_detailed_report)
    assert r1.overall_assessment.overall_score == r2.overall_assessment.overall_score


def test_summary_report_readiness_level_stable(sample_summary_report: dict) -> None:
    s1 = SummaryReport.model_validate(sample_summary_report)
    s2 = SummaryReport.model_validate(sample_summary_report)
    assert s1.readiness_level == s2.readiness_level


# ── local fixtures (self-contained, no conftest dependency) ──────────────────


@pytest.fixture
def sample_detailed_report() -> dict:
    from uuid import uuid4

    return {
        "schema_version": "1.0",
        "format_type": "detailed",
        "session_id": str(uuid4()),
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
            "verdict": "Strong backend candidate.",
        },
        "question_by_question": [],
        "strengths": [],
        "weaknesses": [],
        "improvement_plan": [],
        "interviewer_notes": "Good session.",
    }


@pytest.fixture
def sample_summary_report() -> dict:
    from uuid import uuid4

    return {
        "schema_version": "1.0",
        "format_type": "summary",
        "session_id": str(uuid4()),
        "domain": "backend",
        "completed_at": "2026-05-21T12:00:00",
        "overall_score": 7.5,
        "readiness_level": "ready",
        "verdict": "Strong backend candidate with solid knowledge of async Python and SQL optimization.",
        "top_strengths": ["Async programming", "SQL optimization"],
        "top_weaknesses": ["System design", "Distributed systems"],
        "next_actions": [
            {"action": "Study CAP theorem", "priority": "medium"},
            {"action": "Practice system design", "priority": "high"},
        ],
    }
