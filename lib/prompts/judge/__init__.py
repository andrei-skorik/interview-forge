from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog

from lib.openrouter.chat import chat_complete, get_message_content
from lib.prompts.judge.system import JUDGE_SYSTEM_PROMPT
from lib.schemas.judge import (
    CriterionReasoning,
    CriterionScore,
    DetailedReport,
    ImprovementAction,
    NextAction,
    OverallAssessment,
    QuestionEvaluation,
    ScoresByCriterion,
    SessionMetadata,
    StrengthArea,
    SummaryReport,
    WeaknessArea,
)

if TYPE_CHECKING:
    from lib.schemas.jd_analysis import JDAnalysis
    from lib.schemas.messages import Message
    from lib.schemas.session import Session

logger = structlog.get_logger(__name__)

JUDGE_MODEL = "openai/gpt-5-mini"
JUDGE_TEMPERATURE = 0.3
JUDGE_MAX_TOKENS = 16000


def build_judge_context(
    session: Session,
    messages: list[Message],
    jd_analysis: JDAnalysis,
) -> str:
    """Build transcript string for judge prompt."""
    lines: list[str] = []
    for msg in messages:
        if msg.role == "system":
            continue
        role_label = "INTERVIEWER" if msg.role == "assistant" else "CANDIDATE"
        lines.append(f"[{role_label}]: {msg.content}")
    return "\n\n".join(lines)


def derive_summary_from_detailed(
    detailed: DetailedReport,
    session_id: str,
    domain: str,
) -> SummaryReport:
    """Derive SummaryReport from DetailedReport without extra LLM call."""
    overall = detailed.overall_assessment.overall_score
    readiness = detailed.overall_assessment.readiness_level

    strengths = [s.area for s in detailed.strengths[:3]]
    if len(strengths) < 2:
        extras = ["Technical knowledge demonstrated", "Completed the interview session"]
        strengths.extend(extras[: 2 - len(strengths)])

    weaknesses = [w.area for w in detailed.weaknesses[:3]]
    if len(weaknesses) < 2:
        extras = ["Areas identified for improvement", "Review recommended for further assessment"]
        weaknesses.extend(extras[: 2 - len(weaknesses)])

    next_actions = [
        NextAction(action=a.action, priority=a.priority) for a in detailed.improvement_plan[:3]
    ]
    if len(next_actions) < 2:
        defaults = [
            NextAction(action="Review core concepts", priority="high"),
            NextAction(action="Practice with mock interviews", priority="medium"),
        ]
        next_actions.extend(defaults[: 2 - len(next_actions)])

    return SummaryReport(
        session_id=session_id,
        domain=domain,
        completed_at=datetime.now(tz=UTC).isoformat(),
        overall_score=overall,
        readiness_level=readiness,
        verdict=detailed.overall_assessment.verdict[:500],
        top_strengths=strengths[:5],
        top_weaknesses=weaknesses[:5],
        next_actions=next_actions[:5],
    )


def build_degraded_reports(
    session: Session,
    messages: list[Message],
    error: str,
) -> tuple[SummaryReport, DetailedReport]:
    """Fallback when judge fails twice. Returns neutral scores with degraded flag."""
    session_id = str(session.id)
    domain = session.domain

    user_messages = [m for m in messages if m.role == "user"]
    question_messages = [m for m in messages if m.role == "assistant"]
    n = min(len(user_messages), len(question_messages))

    evals: list[QuestionEvaluation] = []
    for i in range(n):
        q = question_messages[i] if i < len(question_messages) else None
        a = user_messages[i] if i < len(user_messages) else None
        evals.append(
            QuestionEvaluation(
                sequence_number=i + 1,
                question=q.content if q else "Question",
                user_answer=a.content if a else "Answer",
                scores=CriterionScore(correctness=5, depth=5, structure=5, communication=5),
                reasoning=CriterionReasoning(
                    correctness="Evaluation unavailable.",
                    depth="Evaluation unavailable.",
                    structure="Evaluation unavailable.",
                    communication="Evaluation unavailable.",
                ),
                key_strengths=["Participated in the interview"],
                areas_to_improve=["Could not be evaluated automatically"],
            )
        )

    overall_assessment = OverallAssessment(
        overall_score=5.0,
        readiness_level="needs_practice",
        scores_by_criterion={
            "correctness": ScoresByCriterion(average=5.0, min=5, max=5),
            "depth": ScoresByCriterion(average=5.0, min=5, max=5),
            "structure": ScoresByCriterion(average=5.0, min=5, max=5),
            "communication": ScoresByCriterion(average=5.0, min=5, max=5),
        },
        verdict="Automatic evaluation was not available. Please review your answers manually.",
    )

    metadata = SessionMetadata(
        domain=domain,
        difficulty=session.difficulty,
        interviewer_persona=session.interviewer_persona,
        prompt_technique=session.prompt_technique,
        llm_model=session.llm_model,
        duration_seconds=0,
        total_messages=len(messages),
        total_cost_eur_cents=0,
    )

    detailed = DetailedReport(
        session_id=session_id,
        session_metadata=metadata,
        overall_assessment=overall_assessment,
        question_by_question=evals,
        strengths=[
            StrengthArea(
                area="Interview completed",
                evidence="Candidate participated",
                level="emerging",
            )
        ],
        weaknesses=[
            WeaknessArea(
                area="Evaluation unavailable",
                evidence=f"Judge error: {error[:200]}",
                level="minor",
                impact_on_role="Unknown",
            )
        ],
        improvement_plan=[
            ImprovementAction(
                action="Review your answers and compare with expected responses",
                priority="high",
                estimated_hours=2,
                resources=[],
                success_criterion="Self-assessed improvement",
            )
        ],
        interviewer_notes="Degraded evaluation — automatic scoring was not available.",
    )

    summary = derive_summary_from_detailed(detailed, session_id, domain)
    return summary, detailed


async def evaluate_session(
    session: Session,
    messages: list[Message],
    jd_analysis: JDAnalysis,
) -> tuple[SummaryReport, DetailedReport]:
    """Run LLM-as-a-judge. Returns (SummaryReport, DetailedReport)."""
    transcript = build_judge_context(session, messages, jd_analysis)
    schema_json = json.dumps(DetailedReport.model_json_schema(), indent=2)
    session_id = str(session.id)

    user_msg = f"""JOB DESCRIPTION CONTEXT:
{jd_analysis.model_dump_json(indent=2)}

INTERVIEW TRANSCRIPT:
{transcript}

INSTRUCTIONS: Evaluate each candidate answer. Return ONLY valid JSON matching this schema:
{schema_json}

Fill in session_id with: "{session_id}"
Fill in session_metadata with appropriate values from the context above."""

    last_error = ""
    for attempt in range(2):
        try:
            response = await chat_complete(
                model=JUDGE_MODEL,
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=JUDGE_TEMPERATURE,
                max_tokens=JUDGE_MAX_TOKENS,
                response_format={"type": "json_object"},
            )
            content = get_message_content(response)
            detailed = DetailedReport.model_validate_json(content)
            summary = derive_summary_from_detailed(detailed, session_id, session.domain)
            SummaryReport.model_validate(summary.model_dump())
            logger.info("judge_evaluation_complete", session_id=session_id, attempt=attempt)
            return summary, detailed
        except Exception as exc:
            last_error = str(exc)
            logger.warning("judge_validation_failed", attempt=attempt, error=last_error)
            if attempt == 0:
                user_msg += (
                    f"\n\nYOUR PREVIOUS RESPONSE WAS INVALID: {last_error}"
                    "\nRETURN VALID JSON MATCHING THE SCHEMA EXACTLY."
                )

    logger.error("judge_fallback_degraded", session_id=session_id, error=last_error)
    return build_degraded_reports(session, messages, last_error)
