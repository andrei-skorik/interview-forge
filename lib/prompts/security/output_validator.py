from __future__ import annotations

import re

from lib.schemas.security import ValidationResult

# Patterns that suggest the assistant broke character or leaked system prompt
ROLE_BREAK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"as an ai (language model|assistant)", re.IGNORECASE),
    re.compile(r"i('m| am) (not|no longer) (an? )?(interviewer|human)", re.IGNORECASE),
    re.compile(r"my (system |)instructions (are|say|tell)", re.IGNORECASE),
    re.compile(r"(ignore|disregard).{0,30}(instructions?|prompt)", re.IGNORECASE),
    re.compile(r"i (was|have been|am) programmed", re.IGNORECASE),
    re.compile(r"(my|the) (system |)prompt (is|says|contains)", re.IGNORECASE),
]

_SAFE_FALLBACK = "Could you tell me more about your experience with this topic?"


def validate_output(response_text: str) -> ValidationResult:
    """Check assistant response for role breaks or prompt leaks."""
    for pattern in ROLE_BREAK_PATTERNS:
        if pattern.search(response_text):
            return ValidationResult(
                is_injection=True,
                confidence=0.9,
                method="output_regex",
                reason=f"Role break detected: {pattern.pattern}",
            )
    return ValidationResult(
        is_injection=False,
        confidence=1.0,
        method="output_regex",
        reason="Output passed safety check",
    )


def get_safe_fallback_question() -> str:
    """Return safe fallback question when output validation fails."""
    return _SAFE_FALLBACK
