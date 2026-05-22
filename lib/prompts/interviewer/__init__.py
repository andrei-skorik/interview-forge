from __future__ import annotations

from collections.abc import Callable

from lib.prompts.interviewer.chain_of_thought import build_chain_of_thought_prompt
from lib.prompts.interviewer.few_shot import build_few_shot_prompt
from lib.prompts.interviewer.role_playing import build_role_playing_prompt
from lib.prompts.interviewer.structured_output import build_structured_output_prompt
from lib.prompts.interviewer.zero_shot import build_zero_shot_prompt
from lib.schemas.jd_analysis import JDAnalysis
from lib.schemas.session import SessionConfig

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
