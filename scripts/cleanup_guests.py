#!/usr/bin/env python3
"""Delete expired guest sessions. Run daily 3am UTC via GitHub Actions."""

import os
import sys
from datetime import datetime

import structlog

from supabase import Client, create_client

logger = structlog.get_logger(__name__)


def delete_expired_guest_sessions(supabase_client: Client) -> int:
    """Delete sessions where guest_token IS NOT NULL and guest_token_expires_at < NOW().

    Returns the count of deleted rows.
    """
    cutoff_iso = datetime.utcnow().isoformat()
    result = (
        supabase_client.table("sessions")
        .delete()
        .not_.is_("guest_token", "null")
        .lt("guest_token_expires_at", cutoff_iso)
        .execute()
    )
    deleted: list[dict] = result.data if result.data else []
    return len(deleted)


def main() -> None:
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not all([supabase_url, supabase_key]):
        logger.error(
            "missing_env_vars",
            required=["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"],
        )
        sys.exit(1)

    assert supabase_url is not None
    assert supabase_key is not None

    supabase = create_client(supabase_url, supabase_key)

    try:
        count = delete_expired_guest_sessions(supabase)
    except Exception as exc:
        logger.error("cleanup_guests_failed", error=str(exc))
        sys.exit(1)

    logger.info("cleanup_guests_complete", rows_deleted=count)


if __name__ == "__main__":
    structlog.configure(processors=[structlog.dev.ConsoleRenderer()])
    main()
