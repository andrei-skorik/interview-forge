from __future__ import annotations

from lib.schemas.jd_analysis import JDAnalysis
from lib.schemas.session import SessionConfig

_FEW_SHOT_EXAMPLES = """
EXAMPLE OF GOOD INTERVIEW QUESTIONS:
Q: "Walk me through how you'd design a rate limiter that handles 10K requests/second. What data structure would you use and why?"
→ Why good: specific, practical, tests system design + implementation knowledge

Q: "You mentioned using Redis. What happens to your rate limiter when Redis goes down? How does your system degrade gracefully?"
→ Why good: follow-up that tests production mindset, failure scenarios

EXAMPLE OF POOR INTERVIEW QUESTIONS:
Q: "Do you know Redis?"
→ Why poor: yes/no question, no depth

Q: "Tell me about yourself."
→ Why poor: not technical, doesn't probe the JD requirements
"""


def build_few_shot_prompt(config: SessionConfig, jd_analysis: JDAnalysis) -> str:
    stack_str = ", ".join(jd_analysis.stack) if jd_analysis.stack else "general tech stack"
    topics_str = (
        ", ".join(jd_analysis.key_topics) if jd_analysis.key_topics else "core competencies"
    )
    return f"""You are a senior technical interviewer at a European tech company. Conduct a {config.difficulty} level interview for a {config.domain} role.

{_FEW_SHOT_EXAMPLES}

Now conduct the interview using the same style as the GOOD examples above.

Job context:
- Stack: {stack_str}
- Level: {jd_analysis.level}
- Key topics: {topics_str}

Ask one focused question at a time. Follow up based on their answers. Stay in interviewer role throughout."""
