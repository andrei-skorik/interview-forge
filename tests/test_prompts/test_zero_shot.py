"""Tests for zero-shot prompt technique."""

from lib.prompts.interviewer.zero_shot import build_zero_shot_prompt
from lib.schemas.jd_analysis import JDAnalysis
from lib.schemas.session import SessionConfig


def test_returns_non_empty_string(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """build_zero_shot_prompt must return a non-empty string."""
    result = build_zero_shot_prompt(sample_session_config, sample_jd_analysis)
    assert isinstance(result, str)
    assert len(result) > 0


def test_contains_domain(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Prompt must reference the domain from config."""
    result = build_zero_shot_prompt(sample_session_config, sample_jd_analysis)
    assert sample_session_config.domain in result


def test_contains_stack_items(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Prompt must include at least one stack item from jd_analysis."""
    result = build_zero_shot_prompt(sample_session_config, sample_jd_analysis)
    assert any(item in result for item in sample_jd_analysis.stack)


def test_contains_difficulty(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Prompt must reference difficulty level."""
    result = build_zero_shot_prompt(sample_session_config, sample_jd_analysis)
    assert sample_session_config.difficulty in result


def test_contains_key_topics(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Prompt must reference at least one key topic from jd_analysis."""
    result = build_zero_shot_prompt(sample_session_config, sample_jd_analysis)
    assert any(topic in result for topic in sample_jd_analysis.key_topics)


def test_behavioral_domain_uses_fallback_stack(sample_jd: str) -> None:
    """Behavioral domain with no stack should use 'general tech stack' fallback."""
    config = SessionConfig(
        job_description=sample_jd,
        domain="behavioral",
        difficulty="easy",
        response_length="concise",
        interviewer_persona="friendly",
        prompt_technique="zero_shot",
        llm_model="openai/gpt-5-mini",
        temperature=0.7,
        max_tokens=1024,
    )
    jd_no_stack = JDAnalysis(
        stack=[],
        level="mid",
        suggested_domain="behavioral",
        key_topics=[],
        company_type="unknown",
        confidence=0.5,
    )
    result = build_zero_shot_prompt(config, jd_no_stack)
    assert "general tech stack" in result
    assert "core competencies" in result


def test_hard_difficulty_reflected(
    sample_jd: str,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Prompt should reflect 'hard' difficulty when configured."""
    config = SessionConfig(
        job_description=sample_jd,
        domain="backend",
        difficulty="hard",
        response_length="detailed",
        interviewer_persona="strict",
        prompt_technique="zero_shot",
        llm_model="openai/gpt-5-mini",
        temperature=0.7,
        max_tokens=1024,
    )
    result = build_zero_shot_prompt(config, sample_jd_analysis)
    assert "hard" in result
