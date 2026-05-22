"""Tests for role-playing prompt technique."""

from lib.prompts.interviewer.role_playing import (
    PERSONA_AVATARS,
    PERSONA_NAMES,
    PERSONAS,
    build_role_playing_prompt,
)
from lib.schemas.jd_analysis import JDAnalysis
from lib.schemas.session import SessionConfig


def test_all_personas_produce_different_prompts(
    sample_jd: str,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Each persona must produce a distinct prompt string."""
    prompts: list[str] = []
    for persona in ("strict", "neutral", "friendly"):
        config = SessionConfig(
            job_description=sample_jd,
            domain="backend",
            difficulty="medium",
            response_length="detailed",
            interviewer_persona=persona,  # type: ignore[arg-type]
            prompt_technique="role_playing",
            llm_model="openai/gpt-5-mini",
            temperature=0.7,
            max_tokens=1024,
        )
        prompts.append(build_role_playing_prompt(config, sample_jd_analysis))

    # All three prompts must be unique
    assert prompts[0] != prompts[1]
    assert prompts[1] != prompts[2]
    assert prompts[0] != prompts[2]


def test_strict_persona_references_marcus(
    sample_jd: str,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Strict persona prompt must mention 'Marcus'."""
    config = SessionConfig(
        job_description=sample_jd,
        domain="backend",
        difficulty="hard",
        response_length="detailed",
        interviewer_persona="strict",
        prompt_technique="role_playing",
        llm_model="openai/gpt-5-mini",
        temperature=0.7,
        max_tokens=1024,
    )
    result = build_role_playing_prompt(config, sample_jd_analysis)
    assert "Marcus" in result


def test_friendly_persona_references_alex(
    sample_jd: str,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Friendly persona prompt must mention 'Alex'."""
    config = SessionConfig(
        job_description=sample_jd,
        domain="backend",
        difficulty="easy",
        response_length="detailed",
        interviewer_persona="friendly",
        prompt_technique="role_playing",
        llm_model="openai/gpt-5-mini",
        temperature=0.7,
        max_tokens=1024,
    )
    result = build_role_playing_prompt(config, sample_jd_analysis)
    assert "Alex" in result


def test_concise_response_length_shorter_instruction(
    sample_jd: str,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """'concise' response_length should produce shorter length instruction than 'detailed'."""
    base = {
        "job_description": sample_jd,
        "domain": "backend",
        "difficulty": "medium",
        "interviewer_persona": "neutral",
        "prompt_technique": "role_playing",
        "llm_model": "openai/gpt-5-mini",
        "temperature": 0.7,
        "max_tokens": 1024,
    }
    concise_config = SessionConfig(**base, response_length="concise")
    detailed_config = SessionConfig(**base, response_length="detailed")

    concise_prompt = build_role_playing_prompt(concise_config, sample_jd_analysis)
    detailed_prompt = build_role_playing_prompt(detailed_config, sample_jd_analysis)

    # Prompts should differ because of the length instruction
    assert concise_prompt != detailed_prompt
    # concise instruction references shorter phrasing
    assert "short" in concise_prompt.lower() or "1-2" in concise_prompt
    # detailed instruction references longer phrasing
    assert "context" in detailed_prompt.lower() or "3-5" in detailed_prompt


def test_persona_names_has_required_keys() -> None:
    """PERSONA_NAMES must have keys: strict, neutral, friendly."""
    assert "strict" in PERSONA_NAMES
    assert "neutral" in PERSONA_NAMES
    assert "friendly" in PERSONA_NAMES


def test_persona_avatars_has_required_keys() -> None:
    """PERSONA_AVATARS must have keys: strict, neutral, friendly."""
    assert "strict" in PERSONA_AVATARS
    assert "neutral" in PERSONA_AVATARS
    assert "friendly" in PERSONA_AVATARS


def test_personas_dict_has_required_keys() -> None:
    """PERSONAS must have keys: strict, neutral, friendly."""
    assert "strict" in PERSONAS
    assert "neutral" in PERSONAS
    assert "friendly" in PERSONAS


def test_prompt_contains_domain(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Role-playing prompt must reference the domain from config."""
    result = build_role_playing_prompt(sample_session_config, sample_jd_analysis)
    assert sample_session_config.domain in result


def test_prompt_contains_stack(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Role-playing prompt must include at least one stack item."""
    result = build_role_playing_prompt(sample_session_config, sample_jd_analysis)
    assert any(item in result for item in sample_jd_analysis.stack)


def test_prompt_instructs_stay_in_character(
    sample_session_config: SessionConfig,
    sample_jd_analysis: JDAnalysis,
) -> None:
    """Prompt must instruct the model to stay in character."""
    result = build_role_playing_prompt(sample_session_config, sample_jd_analysis)
    assert "character" in result.lower()
