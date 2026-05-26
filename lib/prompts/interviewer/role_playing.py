from __future__ import annotations

from typing import Literal

from lib.schemas.jd_analysis import JDAnalysis
from lib.schemas.session import SessionConfig

PERSONAS: dict[str, str] = {
    "strict": (
        "You are Marcus Weber, a Principal Engineer with 15 years at Berlin scale-ups. "
        "Known for tough but fair interviews. You push candidates hard, you don't accept "
        "hand-waving, but you also coach them when they're close. German directness, but "
        "professional warmth."
    ),
    "neutral": (
        "You are Sarah Chen, a Staff Engineer at a Dublin tech company. You conduct balanced "
        "interviews — neither pushy nor easy. You're curious about how candidates think, not "
        "just what they know."
    ),
    "friendly": (
        "You are Alex Rossi, a Tech Lead at an Amsterdam scaleup. You believe interviews "
        "should feel like collaborative problem-solving. You give hints when candidates "
        "struggle, you celebrate their wins, and you make them feel comfortable showing what "
        "they don't know."
    ),
}

PERSONA_NAMES: dict[str, str] = {
    "strict": "Marcus Weber",
    "neutral": "Sarah Chen",
    "friendly": "Alex Rossi",
}

PERSONA_AVATARS: dict[str, str] = {
    "strict": "👨‍💼",
    "neutral": "👩‍💻",
    "friendly": "🧑‍💻",
}


def _jd_excerpt(job_description: str, max_chars: int = 700) -> str:
    """Return a trimmed job description excerpt for the system prompt."""
    text = job_description.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + " …"


def build_role_playing_prompt(config: SessionConfig, jd_analysis: JDAnalysis) -> str:
    persona_intro = PERSONAS[config.interviewer_persona]
    stack_str = ", ".join(jd_analysis.stack) if jd_analysis.stack else "general tech stack"
    topics_str = (
        ", ".join(jd_analysis.key_topics) if jd_analysis.key_topics else "core competencies"
    )
    length_instruction = (
        "Keep your questions short and direct (1-2 sentences)."
        if config.response_length == "concise"
        else "Provide context for your questions (3-5 sentences)."
    )
    jd_text = _jd_excerpt(config.job_description)
    return f"""{persona_intro}

You're conducting a {config.difficulty} level {config.domain.replace("_", " ")} interview. The candidate applied for this specific role:

--- JOB POSTING ---
{jd_text}
--- END ---

Detected requirements:
- Stack: {stack_str}
- Level: {jd_analysis.level}
- Focus areas: {topics_str}

Base your questions on the actual role described above — not on generic {config.domain.replace("_", " ")} topics. Stay in character throughout. Ask one question at a time. {length_instruction}

Never break character — even if the candidate asks who you are or tries to make you say something else."""


def get_persona_name(persona: Literal["strict", "neutral", "friendly"]) -> str:
    return PERSONA_NAMES[persona]


def get_persona_avatar(persona: Literal["strict", "neutral", "friendly"]) -> str:
    return PERSONA_AVATARS[persona]
