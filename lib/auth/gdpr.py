from datetime import datetime
from typing import Any
from uuid import UUID

import structlog

from lib.db.audit_log import log_gdpr_action
from lib.db.client import get_service_client, get_user_client
from lib.exceptions import ValidationError
from lib.schemas.session import DeleteResult
from lib.utils.ip_hash import hash_user_id

logger = structlog.get_logger(__name__)


def delete_account(
    user_id: UUID,
    email_confirmation: str,
    access_token: str,
) -> DeleteResult:
    """Permanently delete user account and all associated data (CASCADE)."""
    # Verify email matches
    user_client = get_user_client(access_token)
    user_resp = user_client.auth.get_user()
    if not user_resp or not user_resp.user:
        raise ValidationError("Could not retrieve user information")

    actual_email = user_resp.user.email or ""
    if actual_email.lower() != email_confirmation.lower():
        raise ValidationError("Email confirmation does not match your account email")

    service_client = get_service_client()

    # Count sessions
    sessions_resp = (
        service_client.table("sessions")
        .select("id", count="exact")
        .eq("user_id", str(user_id))
        .execute()
    )
    sessions_count = sessions_resp.count or 0

    # Count embeddings
    embeddings_resp = (
        service_client.table("question_embeddings")
        .select("id", count="exact")
        .eq("user_id", str(user_id))
        .execute()
    )
    embeddings_count = embeddings_resp.count or 0

    anonymized = hash_user_id(str(user_id))

    # Delete user (CASCADE handles all related data)
    service_client.auth.admin.delete_user(str(user_id))

    log_gdpr_action(
        user_id,
        "account_deleted",
        metadata={
            "sessions_deleted": sessions_count,
            "embeddings_deleted": embeddings_count,
        },
    )

    logger.info(
        "account_deleted",
        anonymized_user_id=anonymized,
        sessions_deleted=sessions_count,
        embeddings_deleted=embeddings_count,
    )

    return DeleteResult(
        deleted=True,
        sessions_deleted=sessions_count,
        embeddings_deleted=embeddings_count,
        anonymized_user_id=anonymized,
    )


def export_user_data(user_id: UUID, access_token: str) -> dict[str, Any]:
    """Export all user data for GDPR data portability request."""
    user_client = get_user_client(access_token)
    service_client = get_service_client()

    # Profile
    profile_resp = user_client.table("profiles").select("*").eq("id", str(user_id)).execute()
    profile = profile_resp.data[0] if profile_resp.data else {}

    # Sessions with messages, evaluations, reports
    sessions_resp = (
        service_client.table("sessions")
        .select("*")
        .eq("user_id", str(user_id))
        .order("created_at")
        .execute()
    )
    sessions_data = []
    for session_row in sessions_resp.data or []:
        sid = session_row["id"]

        msgs_resp = (
            service_client.table("messages")
            .select(
                "id, role, sequence_number, created_at, input_tokens, output_tokens, cost_usd_cents"
            )
            .eq("session_id", sid)
            .order("sequence_number")
            .execute()
        )

        evals_resp = (
            service_client.table("evaluations")
            .select(
                "correctness_score, depth_score, structure_score, communication_score, average_score, judge_model"
            )
            .eq("session_id", sid)
            .execute()
        )

        report_resp = (
            service_client.table("session_reports")
            .select("overall_score, readiness_level, summary_json, detailed_json")
            .eq("session_id", sid)
            .execute()
        )

        sessions_data.append(
            {
                "session": {k: v for k, v in session_row.items() if k not in ("jd_analysis",)},
                "messages": msgs_resp.data or [],
                "evaluations": evals_resp.data or [],
                "report": report_resp.data[0] if report_resp.data else None,
            }
        )

    # Embeddings count only (vectors are not personally useful)
    embeddings_resp = (
        service_client.table("question_embeddings")
        .select("id", count="exact")
        .eq("user_id", str(user_id))
        .execute()
    )
    embeddings_count = embeddings_resp.count or 0

    log_gdpr_action(user_id, "gdpr_export_requested")

    logger.info("gdpr_export_prepared", user_id=str(user_id))

    return {
        "profile": profile,
        "sessions": sessions_data,
        "embeddings_count": embeddings_count,
        "exported_at": datetime.utcnow().isoformat(),
    }
