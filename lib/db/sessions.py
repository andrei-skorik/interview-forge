import asyncio
import contextlib
import math
import secrets
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import structlog

from lib.db.client import get_service_client, get_user_client
from lib.exceptions import NotFoundError, RateLimitError, UnauthorizedError, ValidationError
from lib.openrouter.chat import chat_complete, get_message_content, get_usage
from lib.openrouter.cost_calculator import calculate_cost
from lib.openrouter.models import get_models_pricing
from lib.prompts.interviewer import get_interviewer_prompt, postprocess_llm_response
from lib.prompts.jd_analyzer import analyze_jd_cached
from lib.prompts.judge import evaluate_session
from lib.prompts.security.input_validator import validate_input
from lib.schemas.jd_analysis import JDAnalysis
from lib.schemas.messages import Message
from lib.schemas.session import (
    CreateSessionResult,
    FinishResult,
    Session,
    SessionConfig,
    SessionCost,
    SessionFilters,
    SessionReportPreview,
    SessionsList,
    SessionWithMessages,
)
from lib.utils.rate_limit import get_rate_limiter

logger = structlog.get_logger(__name__)

JUDGE_MODEL = "openai/gpt-5-mini"


def _row_to_session(row: dict[str, Any]) -> Session:
    return Session.model_validate(row)


def _row_to_message(row: dict[str, Any]) -> Message:
    return Message.model_validate(row)


def _get_eur_rate() -> float:
    try:
        service_client = get_service_client()
        resp = (
            service_client.table("currency_rates")
            .select("rate")
            .order("fetched_at", desc=True)
            .limit(1)
            .execute()
        )
        if resp.data:
            return float(resp.data[0]["rate"])
    except Exception as exc:
        logger.warning("eur_rate_fetch_failed", error=str(exc))
    return 0.92


def create_session(
    config: SessionConfig,
    user_id: UUID | None,
    *,
    ip_hash: str | None = None,
) -> CreateSessionResult:
    """Create a new interview session, generate first question, return result."""
    # Security: validate job description
    validation = asyncio.run(validate_input(config.job_description))
    if validation.is_injection:
        from lib.db.security_events import log_event

        log_event(
            "prompt_injection_blocked",
            "high",
            validation.method,
            user_id=user_id,
            ip_hash=ip_hash,
            input_excerpt=config.job_description[:500],
            detection_confidence=validation.confidence,
            detection_reason=validation.reason,
        )
        from lib.exceptions import PromptInjectionError

        raise PromptInjectionError(validation.reason)

    # Analyze JD — detected domain always wins over sidebar selection
    jd_analysis: JDAnalysis = analyze_jd_cached(config.job_description)
    effective_config = config.model_copy(update={"domain": jd_analysis.suggested_domain})

    # For few_shot technique: generate role-specific example questions once.
    # Stored in jd_analysis.few_shot_examples (persisted in sessions.jd_analysis JSON)
    # so send_message() reuses them without extra LLM calls.
    if config.prompt_technique == "few_shot" and not jd_analysis.few_shot_examples:
        from lib.prompts.interviewer.few_shot import generate_few_shot_examples

        examples = asyncio.run(
            generate_few_shot_examples(jd_analysis, difficulty=config.difficulty)
        )
        if examples:
            jd_analysis = jd_analysis.model_copy(update={"few_shot_examples": examples})

    # Rate limiting
    limiter = get_rate_limiter()
    if user_id is not None:
        allowed = limiter.check_authenticated(str(user_id))
    else:
        allowed = limiter.check_guest(ip_hash or "")
    if not allowed:
        raise RateLimitError("Rate limit exceeded")

    # Guest token
    guest_token: str | None = None
    guest_token_expires_at: datetime | None = None
    if user_id is None:
        guest_token = "gst_" + secrets.token_urlsafe(16)
        guest_token_expires_at = datetime.utcnow() + timedelta(days=7)

    # Always use service_role for session INSERT (RLS would block unauthenticated writes)
    db_client = get_service_client()

    # Build session row
    session_row: dict[str, Any] = {
        "domain": effective_config.domain,  # JD-detected, not sidebar selection
        "difficulty": config.difficulty,
        "response_length": config.response_length,
        "interviewer_persona": config.interviewer_persona,
        "prompt_technique": config.prompt_technique,
        "llm_model": config.llm_model,
        "temperature": config.temperature,
        "top_p": config.top_p,
        "max_tokens": config.max_tokens,
        "frequency_penalty": config.frequency_penalty,
        "presence_penalty": config.presence_penalty,
        "job_description": config.job_description,
        "jd_analysis": jd_analysis.model_dump(),
        "status": "in_progress",
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_cost_usd_cents": 0,
        "share_enabled": False,
    }
    if user_id is not None:
        session_row["user_id"] = str(user_id)
    if guest_token is not None:
        session_row["guest_token"] = guest_token
    if guest_token_expires_at is not None:
        session_row["guest_token_expires_at"] = guest_token_expires_at.isoformat()

    session_resp = db_client.table("sessions").insert(session_row).execute()
    session = _row_to_session(session_resp.data[0])
    session_id = session.id

    # Build system prompt and generate first question
    system_prompt = get_interviewer_prompt(effective_config, jd_analysis)
    messages_for_llm = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Please start the interview."},
    ]
    llm_resp = asyncio.run(
        chat_complete(
            model=config.llm_model,
            messages=messages_for_llm,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            frequency_penalty=config.frequency_penalty,
            presence_penalty=config.presence_penalty,
        )
    )
    assistant_text = get_message_content(llm_resp)
    assistant_text = postprocess_llm_response(
        assistant_text, config.prompt_technique, str(session_id)
    )
    input_tokens, output_tokens = get_usage(llm_resp)

    # Cost calculation
    pricing = get_models_pricing()
    model_pricing = next((m for m in pricing.models if m.id == config.llm_model), None)
    eur_rate = pricing.exchange_rate.rate
    if model_pricing is None:
        cost_breakdown_usd_cents = 0
        cost_breakdown_eur_cents = 0
    else:
        cb = calculate_cost(input_tokens, output_tokens, model_pricing, eur_rate)
        cost_breakdown_usd_cents = cb.usd_cents
        cost_breakdown_eur_cents = cb.eur_cents

    # INSERT first assistant message
    msg_resp = (
        db_client.table("messages")
        .insert(
            {
                "session_id": str(session_id),
                "role": "assistant",
                "content": assistant_text,
                "sequence_number": 1,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd_cents": cost_breakdown_usd_cents,
                "suspicious": False,
                "metadata": {},
            }
        )
        .execute()
    )
    first_message = _row_to_message(msg_resp.data[0])

    # UPDATE session totals
    db_client.table("sessions").update(
        {
            "total_cost_usd_cents": cost_breakdown_usd_cents,
            "total_input_tokens": input_tokens,
            "total_output_tokens": output_tokens,
        }
    ).eq("id", str(session_id)).execute()

    session_cost = SessionCost(
        session_total_usd_cents=cost_breakdown_usd_cents,
        session_total_eur_cents=cost_breakdown_eur_cents,
        last_message_usd_cents=cost_breakdown_usd_cents,
        last_message_eur_cents=cost_breakdown_eur_cents,
    )

    logger.info(
        "session_created",
        session_id=str(session_id),
        user_id=str(user_id) if user_id else None,
        domain=effective_config.domain,
        domain_source="jd_analysis",
    )
    return CreateSessionResult(
        session=session,
        jd_analysis=jd_analysis,
        first_message=first_message,
        cost=session_cost,
    )


def get_session(
    session_id: UUID,
    *,
    access_token: str | None = None,
    guest_token: str | None = None,
    share_token: str | None = None,
) -> SessionWithMessages:
    """Load a session with messages. Enforces access control."""
    service_client = get_service_client()

    if guest_token:
        resp = service_client.table("sessions").select("*").eq("id", str(session_id)).execute()
        if not resp.data:
            raise NotFoundError("Session not found")
        row = resp.data[0]
        if row.get("guest_token") != guest_token:
            raise NotFoundError("Session not found")
        expires_str = row.get("guest_token_expires_at")
        if expires_str:
            expires_at = datetime.fromisoformat(
                expires_str.replace("Z", "+00:00") if expires_str.endswith("Z") else expires_str
            )
            now = datetime.utcnow().replace(tzinfo=expires_at.tzinfo)
            if now > expires_at:
                raise UnauthorizedError("Guest token expired")

    elif share_token:
        resp = service_client.table("sessions").select("*").eq("id", str(session_id)).execute()
        if not resp.data:
            raise NotFoundError("Session not found")
        row = resp.data[0]
        if not row.get("share_enabled") or row.get("share_token") != share_token:
            raise NotFoundError("Session not found")

    elif access_token:
        client = get_user_client(access_token)
        resp = client.table("sessions").select("*").eq("id", str(session_id)).execute()
        if not resp.data:
            raise NotFoundError("Session not found")
        row = resp.data[0]

    else:
        raise UnauthorizedError("No access credentials provided")

    msgs_resp = (
        service_client.table("messages")
        .select("*")
        .eq("session_id", str(session_id))
        .order("sequence_number")
        .execute()
    )
    messages = [_row_to_message(m) for m in (msgs_resp.data or [])]

    result = SessionWithMessages.model_validate(row)
    result.messages = messages
    return result


def list_user_sessions(
    user_id: UUID,
    access_token: str,
    *,
    page: int = 1,
    per_page: int = 20,
    filters: SessionFilters | None = None,
) -> SessionsList:
    """List sessions for the authenticated user with pagination and optional filters."""
    client = get_user_client(access_token)
    query = client.table("sessions").select("*", count="exact")

    if filters:
        if filters.domains:
            query = query.in_("domain", filters.domains)
        if filters.status:
            query = query.eq("status", filters.status)
        if filters.date_from:
            query = query.gte("created_at", filters.date_from.isoformat())
        if filters.date_to:
            query = query.lte("created_at", filters.date_to.isoformat())

    start = (page - 1) * per_page
    end = page * per_page - 1

    resp = query.order("created_at", desc=True).range(start, end).execute()
    sessions = [_row_to_session(r) for r in (resp.data or [])]
    total = resp.count or 0

    return SessionsList(
        sessions=sessions,
        total=total,
        page=page,
        per_page=per_page,
    )


def finish_interview(
    session_id: UUID,
    *,
    access_token: str | None = None,
    guest_token: str | None = None,
) -> FinishResult:
    """Evaluate completed session and persist results."""
    from lib.db.evaluations import save_evaluation

    session_with_msgs = get_session(
        session_id,
        access_token=access_token,
        guest_token=guest_token,
    )

    user_messages = [m for m in session_with_msgs.messages if m.role == "user"]
    if len(user_messages) < 3:
        raise ValidationError("At least 3 answers required to finish the interview")

    service_client = get_service_client()

    # Mark as evaluating
    service_client.table("sessions").update({"status": "evaluating"}).eq(
        "id", str(session_id)
    ).execute()

    jd_analysis_raw = None
    try:
        raw_resp = (
            service_client.table("sessions")
            .select("jd_analysis")
            .eq("id", str(session_id))
            .single()
            .execute()
        )
        jd_analysis_raw = raw_resp.data.get("jd_analysis") if raw_resp.data else None
    except Exception:
        pass

    jd_analysis = (
        JDAnalysis.model_validate(jd_analysis_raw)
        if jd_analysis_raw
        else JDAnalysis(
            stack=[],
            level="unknown",
            suggested_domain=session_with_msgs.domain,
            key_topics=[],
            company_type="unknown",
            confidence=0.0,
        )
    )

    import time

    t0 = time.monotonic()
    summary, detailed = asyncio.run(
        evaluate_session(session_with_msgs, session_with_msgs.messages, jd_analysis)
    )
    generation_time_ms = int((time.monotonic() - t0) * 1000)

    degraded = detailed.overall_assessment.overall_score == 5.0 and all(
        s.area == "Evaluation unavailable" for s in detailed.weaknesses
    )

    # Estimate judge cost
    judge_input_tokens = 2000
    judge_output_tokens = 1500
    eur_rate = _get_eur_rate()
    pricing = get_models_pricing()
    judge_pricing = next((m for m in pricing.models if m.id == JUDGE_MODEL), None)
    judge_cost_usd_cents = 0
    if judge_pricing:
        cb = calculate_cost(judge_input_tokens, judge_output_tokens, judge_pricing, eur_rate)
        judge_cost_usd_cents = cb.usd_cents

    # Save report — upsert so retries after partial failure don't duplicate
    service_client.table("session_reports").upsert(
        {
            "session_id": str(session_id),
            "overall_score": summary.overall_score,
            "readiness_level": summary.readiness_level,
            "strengths": summary.top_strengths,
            "weaknesses": summary.top_weaknesses,
            "improvement_plan": [a.model_dump() for a in summary.next_actions],
            "summary_json": summary.model_dump(),
            "detailed_json": detailed.model_dump(),
            "judge_model": JUDGE_MODEL,
            "cost_usd_cents": judge_cost_usd_cents,
            "generation_time_ms": generation_time_ms,
            "degraded_evaluation": degraded,
        },
        on_conflict="session_id",
    ).execute()

    # Save per-question evaluations (best-effort — don't fail the whole report)
    assistant_msgs = [m for m in session_with_msgs.messages if m.role == "assistant"]
    pairs = list(zip(assistant_msgs, user_messages, strict=False))
    per_eval_cost = math.ceil(judge_cost_usd_cents / max(len(pairs), 1))

    for q_eval in detailed.question_by_question:
        idx = q_eval.sequence_number - 1
        if idx < 0 or idx >= len(pairs):
            continue
        q_msg, a_msg = pairs[idx]
        with contextlib.suppress(Exception):  # non-critical; report already saved
            save_evaluation(
                session_id=session_id,
                question_message_id=q_msg.id,
                answer_message_id=a_msg.id,
                correctness_score=q_eval.scores.correctness,
                depth_score=q_eval.scores.depth,
                structure_score=q_eval.scores.structure,
                communication_score=q_eval.scores.communication,
                correctness_reasoning=q_eval.reasoning.correctness,
                depth_reasoning=q_eval.reasoning.depth,
                structure_reasoning=q_eval.reasoning.structure,
                communication_reasoning=q_eval.reasoning.communication,
                judge_model=JUDGE_MODEL,
                cost_usd_cents=per_eval_cost,
            )

    final_status = "completed_without_eval" if degraded else "completed"
    prev_cost = session_with_msgs.total_cost_usd_cents
    new_total_usd = prev_cost + judge_cost_usd_cents
    new_total_eur = math.ceil(new_total_usd * eur_rate)

    service_client.table("sessions").update(
        {
            "status": final_status,
            "completed_at": datetime.utcnow().isoformat(),
            "total_cost_usd_cents": new_total_usd,
        }
    ).eq("id", str(session_id)).execute()

    report_preview = SessionReportPreview(
        session_id=session_id,
        overall_score=summary.overall_score,
        readiness_level=summary.readiness_level,
    )

    logger.info(
        "session_finished",
        session_id=str(session_id),
        status=final_status,
        score=summary.overall_score,
    )

    return FinishResult(
        session_id=session_id,
        status=final_status,  # type: ignore[arg-type]
        report=report_preview,
        evaluations_count=len(pairs),
        total_cost_usd_cents=new_total_usd,
        total_cost_eur_cents=new_total_eur,
        evaluation_time_ms=0,
    )


def enable_share(session_id: UUID, access_token: str) -> str:
    """Enable share link for a completed session. Returns the share URL."""
    import streamlit as st

    client = get_user_client(access_token)
    # Verify session belongs to user
    check = (
        client.table("sessions")
        .select("id, share_token, share_enabled")
        .eq("id", str(session_id))
        .execute()
    )
    if not check.data:
        raise NotFoundError("Session not found")

    row = check.data[0]
    # Reuse existing share_token if already enabled
    if row.get("share_enabled") and row.get("share_token"):
        token = row["share_token"]
    else:
        token = secrets.token_hex(16)
        service_client = get_service_client()
        service_client.table("sessions").update({"share_enabled": True, "share_token": token}).eq(
            "id", str(session_id)
        ).execute()

    app_url = st.secrets.get("APP_URL", "https://interviewforge.streamlit.app")
    return f"{app_url}/Report?session_id={session_id}&share_token={token}"


def migrate_guest_sessions(
    user_id: UUID,
    guest_tokens: list[str],
) -> list[UUID]:
    """Claim guest sessions after user registers. Generates embeddings for questions."""
    from lib.db.embeddings import add_embedding
    from lib.openrouter.embeddings import get_embedding

    service_client = get_service_client()
    migrated: list[UUID] = []

    for token in guest_tokens:
        try:
            resp = (
                service_client.table("sessions")
                .update(
                    {"user_id": str(user_id), "guest_token": None, "guest_token_expires_at": None}
                )
                .eq("guest_token", token)
                .is_("user_id", "null")
                .gte("guest_token_expires_at", datetime.utcnow().isoformat())
                .execute()
            )
            if not resp.data:
                continue
            session_id = UUID(resp.data[0]["id"])
            domain = resp.data[0].get("domain", "backend")

            msgs_resp = (
                service_client.table("messages")
                .select("*")
                .eq("session_id", str(session_id))
                .eq("role", "assistant")
                .execute()
            )
            for msg_row in msgs_resp.data or []:
                msg = _row_to_message(msg_row)
                try:
                    embedding = asyncio.run(get_embedding(msg.content))
                    add_embedding(
                        user_id=user_id,
                        session_id=session_id,
                        message_id=msg.id,
                        question_text=msg.content,
                        embedding=embedding,
                        domain=domain,
                    )
                except Exception as emb_exc:
                    logger.warning(
                        "migrate_embedding_failed",
                        message_id=str(msg.id),
                        error=str(emb_exc),
                    )

            migrated.append(session_id)
            logger.info(
                "guest_session_migrated",
                session_id=str(session_id),
                user_id=str(user_id),
            )
        except Exception as exc:
            logger.warning(
                "migrate_guest_session_failed",
                token=token[:8],
                error=str(exc),
            )

    return migrated
