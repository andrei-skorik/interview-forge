"""Tests for chain-of-thought prompt technique."""

from lib.prompts.interviewer.chain_of_thought import (
    build_chain_of_thought_prompt,
    extract_question_from_cot,
    extract_thinking_from_cot,
)
from lib.schemas.jd_analysis import JDAnalysis
from lib.schemas.session import SessionConfig


def test_returns_non_empty_string(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """build_chain_of_thought_prompt must return a non-empty string."""
    result = build_chain_of_thought_prompt(sample_session_config, sample_jd_analysis)
    assert isinstance(result, str)
    assert len(result) > 0


def test_prompt_contains_thinking_tag(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Prompt must instruct the model to use <thinking> tags."""
    result = build_chain_of_thought_prompt(sample_session_config, sample_jd_analysis)
    assert "<thinking>" in result


def test_prompt_contains_question_tag(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Prompt must instruct the model to use <question> tags."""
    result = build_chain_of_thought_prompt(sample_session_config, sample_jd_analysis)
    assert "<question>" in result


def test_extract_question_with_tags() -> None:
    """extract_question_from_cot should extract content inside <question> tags."""
    response = "<thinking>Some reasoning here</thinking>\n<question>How do you handle deadlocks?</question>"
    result = extract_question_from_cot(response)
    assert result == "How do you handle deadlocks?"


def test_extract_question_falls_back_to_full_text() -> None:
    """extract_question_from_cot should return full stripped text when no tags present."""
    response = "  What is the difference between process and thread?  "
    result = extract_question_from_cot(response)
    assert result == "What is the difference between process and thread?"


def test_extract_question_multiline_content() -> None:
    """extract_question_from_cot should handle multi-line question content."""
    response = "<thinking>thinking</thinking>\n<question>\nDescribe how you'd design\na rate limiter.\n</question>"
    result = extract_question_from_cot(response)
    assert "rate limiter" in result


def test_extract_thinking_with_tags() -> None:
    """extract_thinking_from_cot should extract content inside <thinking> tags."""
    response = "<thinking>Let me think about this topic deeply.</thinking>\n<question>Question here?</question>"
    result = extract_thinking_from_cot(response)
    assert result == "Let me think about this topic deeply."


def test_extract_thinking_returns_none_without_tags() -> None:
    """extract_thinking_from_cot should return None when no <thinking> tags."""
    response = "Just a plain question without thinking tags."
    result = extract_thinking_from_cot(response)
    assert result is None


def test_extract_question_case_insensitive_tags() -> None:
    """extract_question_from_cot should be case-insensitive for tag matching."""
    response = "<THINKING>reasoning</THINKING>\n<QUESTION>How does GIL work?</QUESTION>"
    result = extract_question_from_cot(response)
    assert result == "How does GIL work?"


def test_prompt_contains_difficulty(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Prompt must reference the difficulty level."""
    result = build_chain_of_thought_prompt(sample_session_config, sample_jd_analysis)
    assert sample_session_config.difficulty in result
