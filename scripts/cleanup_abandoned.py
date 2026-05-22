#!/usr/bin/env python3
"""Mark stale sessions as abandoned or completed_without_eval. Run every 15min via GitHub Actions."""

import os
import sys
from datetime import datetime, timedelta

import structlog

from supabase import Client, create_client

logger = structlog.get_logger(__name__)

ABANDONED_AFTER_HOURS = 2
STUCK_EVALUATING_AFTER_MINUTES = 5


def mark_abandoned_sessions(supabase_client: Client) -> int:
    """Update sessions to 'abandoned' where status='in_progress' and idle for 2+ hours.

    Returns count of updated rows.
    """
    cutoff = (datetime.utcnow() - timedelta(hours=ABANDONED_AFTER_HOURS)).isoformat()
    result = (
        supabase_client.table("sessions")
        .update({"status": "abandoned"})
        .eq("status", "in_progress")
        .lt("updated_at", cutoff)
        .execute()
    )
    updated: list[dict] = result.data if result.data else []
    return len(updated)


def mark_stuck_evaluating_sessions(supabase_client: Client) -> int:
    """Update sessions to 'completed_without_eval' where status='evaluating' and stuck for 5+ min.

    Sessions stuck in 'evaluating' indicate the judge/eval job failed silently.
    Returns count of updated rows.
    """
    cutoff = (datetime.utcnow() - timedelta(minutes=STUCK_EVALUATING_AFTER_MINUTES)).isoformat()
    result = (
        supabase_client.table("sessions")
        .update({"status": "completed_without_eval"})
        .eq("status", "evaluating")
        .lt("updated_at", cutoff)
        .execute()
    )
    updated: list[dict] = result.data if result.data else []
    return len(updated)


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
        abandoned_count = mark_abandoned_sessions(supabase)
        logger.info("marked_abandoned", rows_updated=abandoned_count)

        stuck_count = mark_stuck_evaluating_sessions(supabase)
        logger.info("marked_completed_without_eval", rows_updated=stuck_count)
    except Exception as exc:
        logger.error("cleanup_abandoned_failed", error=str(exc))
        sys.exit(1)

    logger.info(
        "cleanup_abandoned_complete",
        abandoned=abandoned_count,
        completed_without_eval=stuck_count,
    )


if __name__ == "__main__":
    structlog.configure(processors=[structlog.dev.ConsoleRenderer()])
    main()
