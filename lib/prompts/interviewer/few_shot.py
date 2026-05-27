from __future__ import annotations

from lib.schemas.jd_analysis import JDAnalysis
from lib.schemas.session import SessionConfig

# NOTE: these are examples for the MODEL to learn question *style* only.
# The model must NOT copy the "→ Why good/poor:" commentary into its own output.
_FEW_SHOT_EXAMPLES = """
EXAMPLES OF GOOD INTERVIEW QUESTIONS (study style, do NOT copy the annotations):
"Walk me through how you'd design a rate limiter for 10K req/s. What data structure would you use and why?"
"You mentioned Redis — what happens to your rate limiter when Redis goes down? How does your system degrade gracefully?"

EXAMPLES OF POOR QUESTIONS (avoid this style):
"Do you know Redis?" — yes/no, no depth
"Tell me about yourself." — not technical
"""


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
    return f"""You are a senior technical interviewer at a European tech company. Conduct a {config.difficulty} level interview for this specific role:

--- JOB POSTING ---
{jd_text}
--- END ---

{_FEW_SHOT_EXAMPLES}

Conduct the interview using the same QUESTION STYLE as the good examples.

CRITICAL OUTPUT RULES:
- Output ONLY the question text — no "→ Why good:", no meta-commentary, no labels
- Ask one question per turn
- {length_instruction}

Job context:
- Stack: {stack_str}
- Level: {jd_analysis.level}
- Key topics: {topics_str}

Follow up based on the candidate's answers. Stay in interviewer role throughout."""
