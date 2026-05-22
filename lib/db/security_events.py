from typing import Any
from uuid import UUID

import structlog

from lib.db.client import get_service_client

logger = structlog.get_logger(__name__)


def log_event(
    event_type: str,
    severity: str,
    detection_method: str,
    *,
    user_id: UUID | None = None,
    session_id: UUID | None = None,
    ip_hash: str | None = None,
    input_excerpt: str | None = None,
    detection_confidence: float | None = None,
    detection_reason: str | None = None,
    blocked: bool = True,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Log a security event. Never raises."""
    try:
        service_client = get_service_client()
        excerpt = (input_excerpt or "")[:500] or None
        row: dict[str, Any] = {
            "event_type": event_type,
            "severity": severity,
            "detection_method": detection_method,
            "blocked": blocked,
            "metadata": metadata or {},
        }
        if user_id is not None:
            row["user_id"] = str(user_id)
        if session_id is not None:
            row["session_id"] = str(session_id)
        if ip_hash is not None:
            row["ip_hash"] = ip_hash
        if excerpt:
            row["input_excerpt"] = excerpt
        if detection_confidence is not None:
            row["detection_confidence"] = detection_confidence
        if detection_reason is not None:
            row["detection_reason"] = detection_reason

        service_client.table("security_events").insert(row).execute()
    except Exception as exc:
        logger.error(
            "security_event_log_failed",
            event_type=event_type,
            error=str(exc),
        )
