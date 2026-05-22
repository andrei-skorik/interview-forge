import asyncio
import math
from typing import Any
from uuid import UUID

import structlog

from lib.db.client import get_service_client, get_user_client
from lib.db.embeddings import add_embedding, find_similar_questions
from lib.exceptions import UnauthorizedError, ValidationError
from lib.openrouter.chat import chat_complete, get_message_content, get_usage
from lib.openrouter.cost_calculator import calculate_cost
from lib.openrouter.embeddings import get_embedding
from lib.openrouter.models import get_models_pricing
from lib.prompts.interviewer import get_interviewer_prompt
from lib.prompts.security.input_validator import validate_input
from lib.prompts.security.output_validator import get_safe_fallback_question, validate_output
from lib.schemas.jd_analysis import JDAnalysis
from lib.schemas.messages import Message, SendMessageResult, SimilarQuestion
from lib.schemas.session import SessionConfig, SessionCost
from lib.utils.token_counter import count_messages_tokens

logger = structlog.get_logger(__name__)

SUMMARIZE_THRESHOLD = 30_000


def _row_to_message(row: dict[str, Any]) -> Message:
    return Message.model_validate(row)


def _select_client(
    session_row: dict[str, Any],
    access_token: str | None,
    guest_token: str | None,
) -> Any:
    """Return the appropriate Supabase client given access credentials."""
    service_client = get_service_client()
    if guest_token:
        stored_token = session_row.get("guest_token")
        if stored_token != guest_token:
            raise UnauthorizedError("Invalid guest token")
        return service_client
    elif access_token:
        return get_user_client(access_token)
    else:
        raise UnauthorizedError("No access credentials provided")


def send_message(
    session_id: UUID,
    content: str,
    *,
    access_token: str | None = None,
    guest_token: str | None = None,
) -> SendMessageResult:
    """Process a user message and get the next interviewer question."""
    # Validate length
    if not 1 <= len(content) <= 50_000:
        raise ValidationError("Message must be between 1 and 50000 characters")

    # Security validation (async)
    validation = asyncio.run(validate_input(content))
    if validation.is_injection:
        from lib.db.security_events import log_event

        log_event(
            "prompt_injection_blocked",
            "high",
            validation.method,
            session_id=session_id,
            input_excerpt=content[:500],
            detection_confidence=validation.confidence,
            detection_reason=validation.reason,
        )
        from lib.exceptions import PromptInjectionError

        raise PromptInjectionError(validation.reason)

    service_client = get_service_client()

    # Load session
    session_resp = (
        service_client.table("sessions").select("*").eq("id", str(session_id)).single().execute()
    )
    if not session_resp.data:
        from lib.exceptions import NotFoundError

        raise NotFoundError("Session not found")

    session_row = session_resp.data
    _select_client(session_row, access_token, guest_token)  # Access check

    # Get max sequence_number with retry on UniqueViolation
    user_msg = None
    for _attempt in range(3):
        try:
            seq_resp = (
                service_client.table("messages")
                .select("sequence_number")
                .eq("session_id", str(session_id))
                .order("sequence_number", desc=True)
                .limit(1)
                .execute()
            )
            next_seq = seq_resp.data[0]["sequence_number"] + 1 if seq_resp.data else 1
            user_msg_resp = (
                service_client.table("messages")
                .insert(
                    {
                        "session_id": str(session_id),
                        "role": "user",
                        "content": content,
                        "sequence_number": next_seq,
                        "suspicious": False,
                        "metadata": {},
                    }
                )
                .execute()
            )
            user_msg = _row_to_message(user_msg_resp.data[0])
            break
        except Exception as exc:
            err = str(exc).lower()
            if "unique" in err or "duplicate" in err:
                continue
            raise

    if user_msg is None:
        raise ValidationError("Could not insert user message after retries")

    # Load all messages for context
    all_msgs_resp = (
        service_client.table("messages")
        .select("*")
        .eq("session_id", str(session_id))
        .order("sequence_number")
        .execute()
    )
    all_messages = [_row_to_message(r) for r in (all_msgs_resp.data or [])]

    # Build config object from session_row
    config = SessionConfig(
        job_description=session_row.get("job_description", ""),
        domain=session_row["domain"],
        difficulty=session_row["difficulty"],
        response_length=session_row.get("response_length", "detailed"),
        interviewer_persona=session_row["interviewer_persona"],
        prompt_technique=session_row["prompt_technique"],
        llm_model=session_row["llm_model"],
        temperature=float(session_row["temperature"]),
        top_p=float(session_row["top_p"]),
        max_tokens=int(session_row["max_tokens"]),
        frequency_penalty=float(session_row["frequency_penalty"]),
        presence_penalty=float(session_row["presence_penalty"]),
    )

    jd_raw = session_row.get("jd_analysis")
    jd_analysis = (
        JDAnalysis.model_validate(jd_raw)
        if jd_raw
        else JDAnalysis(
            stack=[],
            level="unknown",
            suggested_domain=config.domain,
            key_topics=[],
            company_type="unknown",
            confidence=0.0,
        )
    )

    # Embedding-based similarity (authenticated users only)
    similar_avoided: list[SimilarQuestion] = []
    system_prompt = get_interviewer_prompt(config, jd_analysis)

    user_id_str = session_row.get("user_id")
    if user_id_str:
        user_id = UUID(user_id_str)
        try:
            content_embedding = asyncio.run(get_embedding(content))
            similar = find_similar_questions(
                content_embedding,
                user_id,
                config.domain,
                threshold=0.92,
                max_results=5,
            )
            if similar:
                similar_avoided = similar
                topics = ", ".join(s.question_text[:80] for s in similar)
                system_prompt += f"\n\nAvoid repeating questions about: {topics}"
        except Exception as emb_exc:
            logger.warning("similarity_check_failed", error=str(emb_exc))

    # Build history for OpenRouter
    history_as_dicts = [
        {"role": m.role, "content": m.content}
        for m in all_messages
        if m.role in ("user", "assistant")
    ]

    # Check token count; summarize if needed
    if count_messages_tokens(history_as_dicts) > SUMMARIZE_THRESHOLD:
        try:
            old_messages = history_as_dicts[:-4]
            recent = history_as_dicts[-4:]
            transcript = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in old_messages)
            summary_resp = asyncio.run(
                chat_complete(
                    model="openai/gpt-5-nano",
                    messages=[
                        {
                            "role": "system",
                            "content": "Summarize this interview transcript concisely, preserving key topics and answers.",
                        },
                        {"role": "user", "content": transcript},
                    ],
                    temperature=0.3,
                    max_tokens=512,
                )
            )
            summary_text = get_message_content(summary_resp)
            history_as_dicts = [
                {
                    "role": "assistant",
                    "content": f"[Previous conversation summary: {summary_text}]",
                },
                *recent,
            ]
        except Exception as sum_exc:
            logger.warning("context_summarization_failed", error=str(sum_exc))

    messages_for_llm = [
        {"role": "system", "content": system_prompt},
        *history_as_dicts,
    ]

    # Call OpenRouter
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
    input_tokens, output_tokens = get_usage(llm_resp)

    # Output validation
    out_validation = validate_output(assistant_text)
    suspicious = out_validation.is_injection
    if suspicious:
        assistant_text = get_safe_fallback_question()
        logger.warning(
            "output_validation_failed",
            session_id=str(session_id),
            reason=out_validation.reason,
        )

    # Cost calculation
    pricing = get_models_pricing()
    model_pricing = next((m for m in pricing.models if m.id == config.llm_model), None)
    eur_rate = pricing.exchange_rate.rate
    msg_usd_cents = 0
    msg_eur_cents = 0
    if model_pricing:
        cb = calculate_cost(input_tokens, output_tokens, model_pricing, eur_rate)
        msg_usd_cents = cb.usd_cents
        msg_eur_cents = cb.eur_cents

    # INSERT assistant message
    asst_seq = user_msg.sequence_number + 1
    asst_resp = (
        service_client.table("messages")
        .insert(
            {
                "session_id": str(session_id),
                "role": "assistant",
                "content": assistant_text,
                "sequence_number": asst_seq,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd_cents": msg_usd_cents,
                "suspicious": suspicious,
                "metadata": {},
            }
        )
        .execute()
    )
    assistant_msg = _row_to_message(asst_resp.data[0])

    # Generate embedding for assistant message (authenticated only)
    if user_id_str:
        try:
            asst_embedding = asyncio.run(get_embedding(assistant_text))
            add_embedding(
                user_id=UUID(user_id_str),
                session_id=session_id,
                message_id=assistant_msg.id,
                question_text=assistant_text,
                embedding=asst_embedding,
                domain=config.domain,
            )
        except Exception as emb_exc:
            logger.warning("assistant_embedding_failed", error=str(emb_exc))

    # UPDATE session totals
    prev_usd = session_row.get("total_cost_usd_cents", 0) or 0
    prev_in = session_row.get("total_input_tokens", 0) or 0
    prev_out = session_row.get("total_output_tokens", 0) or 0
    new_total_usd = prev_usd + msg_usd_cents
    new_total_eur = math.ceil(new_total_usd * eur_rate)

    service_client.table("sessions").update(
        {
            "total_cost_usd_cents": new_total_usd,
            "total_input_tokens": prev_in + input_tokens,
            "total_output_tokens": prev_out + output_tokens,
        }
    ).eq("id", str(session_id)).execute()

    cost = SessionCost(
        session_total_usd_cents=new_total_usd,
        session_total_eur_cents=new_total_eur,
        last_message_usd_cents=msg_usd_cents,
        last_message_eur_cents=msg_eur_cents,
    )

    logger.info(
        "message_sent",
        session_id=str(session_id),
        user_seq=user_msg.sequence_number,
        asst_seq=asst_seq,
    )

    return SendMessageResult(
        user_message=user_msg,
        assistant_message=assistant_msg,
        cost=cost,
        similar_questions_avoided=similar_avoided,
    )


def get_messages_by_session(
    session_id: UUID,
    *,
    access_token: str | None = None,
    guest_token: str | None = None,
) -> list[Message]:
    """Return messages for a session ordered by sequence_number."""
    service_client = get_service_client()

    # Verify access
    session_resp = (
        service_client.table("sessions")
        .select("user_id, guest_token, guest_token_expires_at")
        .eq("id", str(session_id))
        .single()
        .execute()
    )
    if not session_resp.data:
        from lib.exceptions import NotFoundError

        raise NotFoundError("Session not found")

    session_row = session_resp.data

    if guest_token:
        if session_row.get("guest_token") != guest_token:
            raise UnauthorizedError("Invalid guest token")
    elif access_token:
        client = get_user_client(access_token)
        check = client.table("sessions").select("id").eq("id", str(session_id)).execute()
        if not check.data:
            from lib.exceptions import NotFoundError

            raise NotFoundError("Session not found")
    else:
        raise UnauthorizedError("No access credentials provided")

    msgs_resp = (
        service_client.table("messages")
        .select("*")
        .eq("session_id", str(session_id))
        .order("sequence_number")
        .execute()
    )
    return [_row_to_message(r) for r in (msgs_resp.data or [])]
