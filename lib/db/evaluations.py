from typing import Any
from uuid import UUID

import structlog

from lib.db.client import get_service_client, get_user_client
from lib.exceptions import NotFoundError, UnauthorizedError
from lib.schemas.session import SessionReportPreview


class FullReport:
    """Holds both JSON blobs for the report page."""

    def __init__(
        self,
        session_id: str,
        overall_score: float,
        readiness_level: str,
        summary_json: dict[str, Any],
        detailed_json: dict[str, Any],
    ) -> None:
        self.session_id = session_id
        self.overall_score = overall_score
        self.readiness_level = readiness_level
        self.summary_json = summary_json
        self.detailed_json = detailed_json


logger = structlog.get_logger(__name__)


def save_evaluation(
    session_id: UUID,
    question_message_id: UUID,
    answer_message_id: UUID,
    correctness_score: int,
    depth_score: int,
    structure_score: int,
    communication_score: int,
    correctness_reasoning: str,
    depth_reasoning: str,
    structure_reasoning: str,
    communication_reasoning: str,
    judge_model: str,
    cost_usd_cents: int,
) -> None:
    """Insert a per-question evaluation row via service role."""
    service_client = get_service_client()
    service_client.table("evaluations").insert(
        {
            "session_id": str(session_id),
            "question_message_id": str(question_message_id),
            "answer_message_id": str(answer_message_id),
            "correctness_score": correctness_score,
            "depth_score": depth_score,
            "structure_score": structure_score,
            "communication_score": communication_score,
            # average_score is GENERATED ALWAYS AS — cannot be inserted manually
            "correctness_reasoning": correctness_reasoning,
            "depth_reasoning": depth_reasoning,
            "structure_reasoning": structure_reasoning,
            "communication_reasoning": communication_reasoning,
            "judge_model": judge_model,
            "cost_usd_cents": cost_usd_cents,
        }
    ).execute()


def get_report(
    session_id: UUID,
    *,
    access_token: str | None = None,
    guest_token: str | None = None,
    share_token: str | None = None,
) -> SessionReportPreview | None:
    """Fetch the session report preview. Returns None if not found."""
    service_client = get_service_client()

    # First verify access to the session itself
    session_resp = (
        service_client.table("sessions")
        .select("id, user_id, guest_token, guest_token_expires_at, share_token, share_enabled")
        .eq("id", str(session_id))
        .execute()
    )
    if not session_resp.data:
        return None

    row = session_resp.data[0]

    if share_token:
        if not row.get("share_enabled") or row.get("share_token") != share_token:
            raise UnauthorizedError("Invalid share token")
    elif guest_token:
        from datetime import datetime

        expires_str = row.get("guest_token_expires_at")
        if row.get("guest_token") != guest_token:
            raise UnauthorizedError("Invalid guest token")
        if expires_str:
            expires_at = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
            if datetime.utcnow().replace(tzinfo=expires_at.tzinfo) > expires_at:
                raise UnauthorizedError("Guest token expired")
    elif access_token:
        client = get_user_client(access_token)
        check = client.table("sessions").select("id").eq("id", str(session_id)).execute()
        if not check.data:
            raise NotFoundError("Session not found")
    else:
        raise UnauthorizedError("No access credentials provided")

    report_resp = (
        service_client.table("session_reports")
        .select("session_id, overall_score, readiness_level")
        .eq("session_id", str(session_id))
        .execute()
    )
    if not report_resp.data:
        return None

    r = report_resp.data[0]
    return SessionReportPreview(
        session_id=r["session_id"],
        overall_score=float(r["overall_score"]),
        readiness_level=r["readiness_level"],
    )


def get_full_report(
    session_id: UUID,
    *,
    access_token: str | None = None,
    guest_token: str | None = None,
    share_token: str | None = None,
) -> FullReport | None:
    """Fetch full report with summary_json and detailed_json. Returns None if not found."""
    service_client = get_service_client()

    # Verify access to session
    session_resp = (
        service_client.table("sessions")
        .select("id, user_id, guest_token, guest_token_expires_at, share_token, share_enabled")
        .eq("id", str(session_id))
        .execute()
    )
    if not session_resp.data:
        return None

    row = session_resp.data[0]

    if share_token:
        if not row.get("share_enabled") or row.get("share_token") != share_token:
            raise UnauthorizedError("Invalid share token")
    elif guest_token:
        from datetime import datetime

        expires_str = row.get("guest_token_expires_at")
        if row.get("guest_token") != guest_token:
            raise UnauthorizedError("Invalid guest token")
        if expires_str:
            expires_at = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
            if datetime.utcnow().replace(tzinfo=expires_at.tzinfo) > expires_at:
                raise UnauthorizedError("Guest token expired")
    elif access_token:
        client = get_user_client(access_token)
        check = client.table("sessions").select("id").eq("id", str(session_id)).execute()
        if not check.data:
            raise NotFoundError("Session not found")
    else:
        raise UnauthorizedError("No access credentials provided")

    report_resp = (
        service_client.table("session_reports")
        .select("session_id, overall_score, readiness_level, summary_json, detailed_json")
        .eq("session_id", str(session_id))
        .execute()
    )
    if not report_resp.data:
        return None

    r = report_resp.data[0]
    return FullReport(
        session_id=r["session_id"],
        overall_score=float(r["overall_score"]),
        readiness_level=r["readiness_level"],
        summary_json=r.get("summary_json") or {},
        detailed_json=r.get("detailed_json") or {},
    )


def get_scores_by_technique(user_id: UUID, access_token: str) -> dict[str, float]:
    """Return avg evaluation scores grouped by prompt_technique for admin stats."""
    client = get_user_client(access_token)
    response = client.rpc(
        "get_scores_by_technique",
        {"target_user_id": str(user_id)},
    ).execute()
    result: dict[str, float] = {}
    for row in response.data or []:
        technique = row.get("prompt_technique") or row.get("technique")
        score = row.get("avg_score") or row.get("average_score")
        if technique and score is not None:
            result[technique] = float(score)
    return result
