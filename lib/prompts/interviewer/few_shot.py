from __future__ import annotations

import structlog
from pydantic import BaseModel, Field

from lib.openrouter.chat import chat_complete, get_message_content
from lib.schemas.jd_analysis import JDAnalysis
from lib.schemas.session import SessionConfig

logger = structlog.get_logger(__name__)

# ── Few-shot example generator ────────────────────────────────────────────────

_GENERATOR_SYSTEM = """You are an expert technical interviewer. Generate exactly 2 realistic interview questions for the role described.

OUTPUT: valid JSON only — {"examples": ["question 1", "question 2"]}

Rules for each question:
- Concrete scenario tied to the actual stack/domain, not a generic topic
- Practical: describes a realistic situation the candidate would face on the job
- Multi-part or implies follow-up thinking (not yes/no)
- 1-3 sentences each
- Do NOT include answer, hints, or meta-commentary — only the question text"""


class _FewShotResponse(BaseModel):
    examples: list[str] = Field(min_length=1, max_length=3)


async def generate_few_shot_examples(
    jd_analysis: JDAnalysis,
    difficulty: str = "medium",
) -> list[str]:
    """Generate 2 domain-specific example questions via gpt-5-nano.

    Returns an empty list on any failure — caller falls back to static examples.
    """
    stack_str = ", ".join(jd_analysis.stack[:6]) if jd_analysis.stack else "general tech stack"
    topics_str = ", ".join(jd_analysis.key_topics[:5]) if jd_analysis.key_topics else "core competencies"
    user_msg = (
        f"Domain: {jd_analysis.suggested_domain}\n"
        f"Stack: {stack_str}\n"
        f"Key topics: {topics_str}\n"
        f"Level: {jd_analysis.level}\n"
        f"Difficulty: {difficulty}\n\n"
        "Generate 2 interview questions for this specific role."
    )
    try:
        response = await chat_complete(
            model="openai/gpt-5-nano",
            messages=[
                {"role": "system", "content": _GENERATOR_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        content = get_message_content(response)
        parsed = _FewShotResponse.model_validate_json(content)
        logger.info(
            "few_shot_examples_generated",
            domain=jd_analysis.suggested_domain,
            count=len(parsed.examples),
        )
        return parsed.examples
    except Exception as exc:
        logger.warning("few_shot_examples_failed", error=str(exc))
        return []


# ── Static fallback (used only when generation fails) ────────────────────────

_STATIC_FALLBACK = [
    "Walk me through a time you had to debug a production issue under pressure. "
    "What was your diagnostic process and how did you communicate with the team?",
    "You're handed a codebase with no documentation and a failing test suite. "
    "Where do you start and how do you build confidence before making changes?",
]


# ── Prompt builder ─────────────────────────────────────────────────────────────

def _jd_excerpt(job_description: str, max_chars: int = 700) -> str:
    text = job_description.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + " …"


def build_few_shot_prompt(config: SessionConfig, jd_analysis: JDAnalysis) -> str:
    stack_str = ", ".join(jd_analysis.stack) if jd_analysis.stack else "general tech stack"
    topics_str = (
        ", ".join(jd_analysis.key_topics) if jd_analysis.key_topics else "core competencies"
    )
    jd_text = _jd_excerpt(config.job_description)
    length_instruction = (
        "Keep each question to 1-2 sentences."
        if config.response_length == "concise"
        else "Keep each question to 2-4 sentences."
    )

    examples = jd_analysis.few_shot_examples or _STATIC_FALLBACK
    examples_block = "\n".join(f'- "{q}"' for q in examples)

    return f"""You are a senior technical interviewer at a European tech company. Conduct a {config.difficulty} level interview for this specific role:

--- JOB POSTING ---
{jd_text}
--- END ---

EXAMPLE QUESTIONS FOR THIS ROLE (study the style and specificity):
{examples_block}

Conduct the interview using the same style as the examples above — concrete scenarios, role-specific, practical.

CRITICAL OUTPUT RULES:
- Output ONLY the question text — no annotations, no labels, no meta-commentary
- Ask one question per turn
- {length_instruction}

Job context:
- Stack: {stack_str}
- Level: {jd_analysis.level}
- Key topics: {topics_str}

Follow up based on the candidate's answers. Stay in interviewer role throughout."""
