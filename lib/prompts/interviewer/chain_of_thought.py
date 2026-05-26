from __future__ import annotations

import re

from lib.schemas.jd_analysis import JDAnalysis
from lib.schemas.session import SessionConfig


def _jd_excerpt(job_description: str, max_chars: int = 700) -> str:
    text = job_description.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + " …"


def build_chain_of_thought_prompt(config: SessionConfig, jd_analysis: JDAnalysis) -> str:
    stack_str = ", ".join(jd_analysis.stack) if jd_analysis.stack else "general tech stack"
    topics_str = (
        ", ".join(jd_analysis.key_topics) if jd_analysis.key_topics else "core competencies"
    )
    jd_text = _jd_excerpt(config.job_description)
    return f"""You are a senior technical interviewer. Before each question, think step by step:

1. What does this specific role actually require? (see job posting below)
2. What level is the candidate at? (review their previous answers)
3. What requirement from the JD have we not covered yet?
4. What kind of question would test that at {config.difficulty} level?
5. What would a good answer look like?

Then ask the question.

--- JOB POSTING ---
{jd_text}
--- END ---

JD stack: {stack_str}
Topics to cover: {topics_str}

Format each turn as:
<thinking>your reasoning</thinking>
<question>your actual question to the candidate</question>

The candidate will only see the question."""


def extract_question_from_cot(response_text: str) -> str:
    """Extract <question> tag content from CoT response. Falls back to full text."""
    match = re.search(r"<question>(.*?)</question>", response_text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return response_text.strip()


def extract_thinking_from_cot(response_text: str) -> str | None:
    """Extract <thinking> tag for debug logging."""
    match = re.search(r"<thinking>(.*?)</thinking>", response_text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None
