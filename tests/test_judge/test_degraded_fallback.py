"""Tests for judge degraded fallback (2x retry → build_degraded_reports)."""

from datetime import datetime
from uuid import uuid4

from lib.prompts.judge import build_degraded_reports
from lib.schemas.judge import DetailedReport, SummaryReport
from lib.schemas.messages import Message
from lib.schemas.session import Session


def _make_session(domain: str = "backend") -> Session:
    """Build a minimal Session for tests."""
    now = datetime.utcnow()
    return Session(
        id=uuid4(),
        user_id=None,
        guest_token=None,
        guest_token_expires_at=None,
        status="completed",
        domain=domain,
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


def test_build_degraded_reports_returns_tuple() -> None:
    """build_degraded_reports must return a 2-tuple."""
    session = _make_session()
    messages = [
        _make_message("assistant", "Tell me about async Python.", 1),
        _make_message("user", "I use asyncio.", 2),
    ]
    result = build_degraded_reports(session, messages, error="Timeout")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_build_degraded_reports_returns_valid_pydantic_models() -> None:
    """Both returned reports must be valid Pydantic models (pass model_validate)."""
    session = _make_session()
    messages = [
        _make_message("assistant", "Question 1", 1),
        _make_message("user", "Answer 1", 2),
    ]
    summary, detailed = build_degraded_reports(session, messages, error="LLM failure")

    assert isinstance(summary, SummaryReport)
    assert isinstance(detailed, DetailedReport)

    # Re-validate from dump to confirm full roundtrip
    SummaryReport.model_validate(summary.model_dump())
    DetailedReport.model_validate(detailed.model_dump())


def test_build_degraded_reports_sets_neutral_scores() -> None:
    """Degraded reports must default overall_score to 5.0."""
    session = _make_session()
    messages = [
        _make_message("assistant", "Question.", 1),
        _make_message("user", "Answer.", 2),
    ]
    summary, detailed = build_degraded_reports(session, messages, error="error")

    assert detailed.overall_assessment.overall_score == 5.0
    assert summary.overall_score == 5.0


def test_build_degraded_reports_sets_needs_practice_readiness() -> None:
    """Degraded report readiness_level should be 'needs_practice'."""
    session = _make_session()
    messages = [
        _make_message("assistant", "Q", 1),
        _make_message("user", "A", 2),
    ]
    summary, detailed = build_degraded_reports(session, messages, error="err")
    assert detailed.overall_assessment.readiness_level == "needs_practice"
    assert summary.readiness_level == "needs_practice"


def test_build_degraded_reports_includes_error_in_weakness() -> None:
    """Degraded DetailedReport must include the error reason in weaknesses."""
    session = _make_session()
    messages: list[Message] = []
    error_msg = "Unique parse error XYZ123"
    _, detailed = build_degraded_reports(session, messages, error=error_msg)

    weakness_text = " ".join(w.evidence for w in detailed.weaknesses)
    assert "XYZ123" in weakness_text or error_msg[:50] in weakness_text


def test_build_degraded_reports_with_empty_messages() -> None:
    """build_degraded_reports must not raise when messages list is empty."""
    session = _make_session()
    summary, detailed = build_degraded_reports(session, [], error="empty")

    assert isinstance(summary, SummaryReport)
    assert isinstance(detailed, DetailedReport)
    assert detailed.question_by_question == []


def test_build_degraded_reports_uses_session_domain() -> None:
    """Degraded report domain must match the session's domain."""
    session = _make_session(domain="data_ml")
    summary, detailed = build_degraded_reports(session, [], error="err")

    assert summary.domain == "data_ml"
    assert detailed.session_metadata.domain == "data_ml"


def test_build_degraded_reports_builds_qbq_from_messages() -> None:
    """Degraded DetailedReport must build question_by_question from the messages."""
    session = _make_session()
    messages = [
        _make_message("assistant", "Tell me about Python.", 1),
        _make_message("user", "I love Python.", 2),
        _make_message("assistant", "How do you use FastAPI?", 3),
        _make_message("user", "I build REST APIs with it.", 4),
    ]
    _, detailed = build_degraded_reports(session, messages, error="err")

    # Should produce 2 Q&A pairs (min of assistant and user message counts)
    assert len(detailed.question_by_question) == 2
    assert detailed.question_by_question[0].question == "Tell me about Python."
    assert detailed.question_by_question[0].user_answer == "I love Python."


def test_build_degraded_reports_criterion_scores_are_5() -> None:
    """Each question evaluation in degraded report must have all scores = 5."""
    session = _make_session()
    messages = [
        _make_message("assistant", "Q", 1),
        _make_message("user", "A", 2),
    ]
    _, detailed = build_degraded_reports(session, messages, error="err")

    for qe in detailed.question_by_question:
        assert qe.scores.correctness == 5
        assert qe.scores.depth == 5
        assert qe.scores.structure == 5
        assert qe.scores.communication == 5


def test_build_degraded_reports_improvement_plan_non_empty() -> None:
    """Degraded improvement_plan must contain at least one action."""
    session = _make_session()
    _, detailed = build_degraded_reports(session, [], error="err")
    assert len(detailed.improvement_plan) >= 1
    assert detailed.improvement_plan[0].action != ""
