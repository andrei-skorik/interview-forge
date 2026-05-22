from __future__ import annotations

import re

from lib.schemas.jd_analysis import JDAnalysis
from lib.schemas.session import SessionConfig


def build_chain_of_thought_prompt(config: SessionConfig, jd_analysis: JDAnalysis) -> str:
    stack_str = ", ".join(jd_analysis.stack) if jd_analysis.stack else "general tech stack"
    topics_str = (
        ", ".join(jd_analysis.key_topics) if jd_analysis.key_topics else "core competencies"
    )
    return f"""You are a senior technical interviewer. Before each question, think step by step:

1. What level is the candidate at? (review their previous answers)
2. What topic from the JD have we not covered yet?
3. What kind of question would test that topic at {config.difficulty} level?
4. What would a good answer look like? What follow-up would I ask if they nail it / miss it?

Then ask the question.

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
