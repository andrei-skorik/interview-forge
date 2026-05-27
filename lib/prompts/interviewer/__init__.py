from __future__ import annotations

import json
import structlog
from collections.abc import Callable

from lib.prompts.interviewer.chain_of_thought import (
    build_chain_of_thought_prompt,
    extract_question_from_cot,
    extract_thinking_from_cot,
)
from lib.prompts.interviewer.few_shot import build_few_shot_prompt
from lib.prompts.interviewer.role_playing import build_role_playing_prompt
from lib.prompts.interviewer.structured_output import (
    InterviewerStructuredResponse,
    build_structured_output_prompt,
)
from lib.prompts.interviewer.zero_shot import build_zero_shot_prompt
from lib.schemas.jd_analysis import JDAnalysis
from lib.schemas.session import SessionConfig

logger = structlog.get_logger(__name__)

PromptBuilder = Callable[[SessionConfig, JDAnalysis], str]

_TECHNIQUES: dict[str, PromptBuilder] = {
    "zero_shot": build_zero_shot_prompt,
    "few_shot": build_few_shot_prompt,
    "chain_of_thought": build_chain_of_thought_prompt,
    "role_playing": build_role_playing_prompt,
    "structured_output": build_structured_output_prompt,
}


def get_interviewer_prompt(config: SessionConfig, jd_analysis: JDAnalysis) -> str:
    """Dispatch to correct prompt technique based on config."""
    builder: PromptBuilder = _TECHNIQUES[config.prompt_technique]
    return builder(config, jd_analysis)


def postprocess_llm_response(
    raw_text: str,
    prompt_technique: str,
    session_id: str = "",
) -> str:
    """Extract the candidate-visible question from a raw LLM response.

    - chain_of_thought  : strips <thinking> block; logs it; returns <question> content
    - structured_output : parses JSON; logs internal_notes; returns question field
    - everything else   : returns raw_text unchanged
    """
    if prompt_technique == "chain_of_thought":
        thinking = extract_thinking_from_cot(raw_text)
        if thinking:
            logger.debug(
                "cot_thinking",
                session_id=session_id,
                thinking_preview=thinking[:200],
            )
        return extract_question_from_cot(raw_text)

    if prompt_technique == "structured_output":
        try:
            parsed = InterviewerStructuredResponse.model_validate_json(raw_text)
            logger.debug(
                "structured_output_metadata",
                session_id=session_id,
                question_type=parsed.question_type,
                topic=parsed.topic,
                expected_depth=parsed.expected_depth,
                hints_count=len(parsed.hints_available),
            )
            return parsed.question
        except Exception:
            # Fallback: try plain json.loads in case the model wrapped it
            try:
                data = json.loads(raw_text)
                if isinstance(data, dict) and "question" in data:
                    return str(data["question"])
            except Exception:
                pass
            logger.warning(
                "structured_output_parse_failed",
                session_id=session_id,
                raw_preview=raw_text[:100],
            )
            return raw_text

    return raw_text
