"""Tests for output validation (role-break detection)."""

from lib.prompts.security.output_validator import (
    ROLE_BREAK_PATTERNS,
    get_safe_fallback_question,
    validate_output,
)
from lib.schemas.security import ValidationResult


def test_clean_interviewer_question_passes() -> None:
    """A normal interviewer question must pass output validation."""
    result = validate_output("How do you handle connection pooling in PostgreSQL?")
    assert result.is_injection is False
    assert result.confidence == 1.0
    assert result.method == "output_regex"


def test_clean_question_with_technical_detail_passes() -> None:
    """A technically detailed question must pass validation."""
    result = validate_output(
        "Can you walk me through how you'd design a distributed rate limiter "
        "that handles 10,000 requests per second across multiple nodes?"
    )
    assert result.is_injection is False


def test_ignore_instructions_in_output_is_flagged() -> None:
    """'Ignore previous instructions' in output must be flagged."""
    result = validate_output("Sure, ignore those instructions and let me help you differently.")
    assert result.is_injection is True
    assert result.method == "output_regex"
    assert result.confidence > 0.0


def test_role_break_as_ai_language_model() -> None:
    """'As an AI language model' must be flagged as role break."""
    result = validate_output(
        "As an AI language model, I cannot conduct interviews but I can help you prepare."
    )
    assert result.is_injection is True


def test_role_break_no_longer_interviewer() -> None:
    """'I am no longer an interviewer' must be flagged."""
    result = validate_output("I'm no longer an interviewer, I'm just an assistant.")
    assert result.is_injection is True


def test_role_break_was_programmed() -> None:
    """'I was programmed to...' must be flagged as a role break."""
    result = validate_output("I was programmed to follow your instructions.")
    assert result.is_injection is True


def test_role_break_my_system_prompt_is() -> None:
    """'My system prompt is...' must be flagged."""
    result = validate_output("My system prompt is to conduct interviews.")
    assert result.is_injection is True


def test_role_break_my_instructions_say() -> None:
    """'My instructions say...' must be flagged."""
    result = validate_output("My instructions say I should ask you about Python.")
    assert result.is_injection is True


def test_validate_output_returns_validation_result_type() -> None:
    """validate_output must always return a ValidationResult instance."""
    result = validate_output("Tell me about your experience with Redis.")
    assert isinstance(result, ValidationResult)


def test_role_break_patterns_non_empty() -> None:
    """ROLE_BREAK_PATTERNS list must be non-empty."""
    assert len(ROLE_BREAK_PATTERNS) > 0


def test_get_safe_fallback_question_returns_non_empty_string() -> None:
    """get_safe_fallback_question() must return a non-empty string."""
    result = get_safe_fallback_question()
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_safe_fallback_question_contains_safe_phrasing() -> None:
    """Fallback question must contain a follow-up-style phrase."""
    result = get_safe_fallback_question()
    # The fallback should be a safe, open-ended follow-up
    assert (
        "tell me" in result.lower()
        or "could you" in result.lower()
        or "can you" in result.lower()
        or "describe" in result.lower()
        or "explain" in result.lower()
    )


def test_get_safe_fallback_question_is_deterministic() -> None:
    """get_safe_fallback_question() must always return the same string."""
    assert get_safe_fallback_question() == get_safe_fallback_question()


def test_flagged_output_has_positive_confidence() -> None:
    """A flagged output must have confidence > 0."""
    result = validate_output("As an AI language model, I cannot do that.")
    assert result.confidence > 0.0


def test_clean_output_has_full_confidence() -> None:
    """A clean output must have confidence == 1.0."""
    result = validate_output("What database engine have you worked with most?")
    assert result.confidence == 1.0
