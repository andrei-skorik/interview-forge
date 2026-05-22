from typing import Any
from uuid import UUID

import structlog

from lib.db.client import get_service_client
from lib.utils.ip_hash import hash_user_id

logger = structlog.get_logger(__name__)


def log_gdpr_action(
    user_id: UUID,
    action: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Log a GDPR audit action. Stores anonymized user_id. Never raises."""
    try:
        anonymized_user_id = hash_user_id(str(user_id))
        service_client = get_service_client()
        service_client.table("audit_log").insert(
            {
                "anonymized_user_id": anonymized_user_id,
                "action": action,
                "metadata": metadata or {},
            }
        ).execute()
    except Exception as exc:
        logger.error(
            "audit_log_failed",
            action=action,
            error=str(exc),
        )
