"""Tests for few-shot prompt technique."""

from lib.prompts.interviewer.few_shot import build_few_shot_prompt
from lib.schemas.jd_analysis import JDAnalysis
from lib.schemas.session import SessionConfig


def test_returns_non_empty_string(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """build_few_shot_prompt must return a non-empty string."""
    result = build_few_shot_prompt(sample_session_config, sample_jd_analysis)
    assert isinstance(result, str)
    assert len(result) > 0


def test_contains_example_patterns(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Prompt must include good/bad example patterns."""
    result = build_few_shot_prompt(sample_session_config, sample_jd_analysis)
    # The prompt should reference example-related keywords
    assert "EXAMPLE" in result or "example" in result.lower()


def test_contains_good_example_marker(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Prompt must include reference to good question examples."""
    result = build_few_shot_prompt(sample_session_config, sample_jd_analysis)
    assert "good" in result.lower() or "GOOD" in result


def test_contains_poor_example_marker(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Prompt must include reference to poor question examples."""
    result = build_few_shot_prompt(sample_session_config, sample_jd_analysis)
    assert "poor" in result.lower() or "bad" in result.lower() or "POOR" in result


def test_contains_domain(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Prompt must reference the domain."""
    result = build_few_shot_prompt(sample_session_config, sample_jd_analysis)
    assert sample_session_config.domain in result


def test_contains_stack(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Prompt must include at least one stack item."""
    result = build_few_shot_prompt(sample_session_config, sample_jd_analysis)
    assert any(item in result for item in sample_jd_analysis.stack)


def test_contains_level(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Prompt must include the experience level from jd_analysis."""
    result = build_few_shot_prompt(sample_session_config, sample_jd_analysis)
    assert sample_jd_analysis.level in result


def test_empty_stack_uses_fallback(sample_jd: str) -> None:
    """Empty stack should produce 'general tech stack' fallback."""
    config = SessionConfig(
        job_description=sample_jd,
        domain="devops",
        difficulty="medium",
        response_length="detailed",
        interviewer_persona="neutral",
        prompt_technique="few_shot",
        llm_model="openai/gpt-5-mini",
        temperature=0.7,
        max_tokens=1024,
    )
    jd = JDAnalysis(
        stack=[],
        level="mid",
        suggested_domain="devops",
        key_topics=[],
        company_type="enterprise",
        confidence=0.6,
    )
    result = build_few_shot_prompt(config, jd)
    assert "general tech stack" in result
