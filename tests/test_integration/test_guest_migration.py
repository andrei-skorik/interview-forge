"""Test guest session migration to a registered user account.

Requires SUPABASE_URL env var (integration test).
"""

import os
from uuid import UUID, uuid4

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("SUPABASE_URL"),
    reason="Integration test requires SUPABASE_URL",
)

SAMPLE_JD = """
Backend Engineer role at Amsterdam startup. 3+ years Python, FastAPI, PostgreSQL.
Experience with Docker, CI/CD, async programming. Strong SQL skills required.
"""


@pytest.mark.integration
def test_guest_session_migrates_to_user() -> None:
    """Guest session should be claimed by a newly registered user."""
    from lib.db.client import get_service_client
    from lib.db.sessions import create_session, migrate_guest_sessions
    from lib.schemas.session import SessionConfig

    config = SessionConfig(
        job_description=SAMPLE_JD,
        domain="backend",
        difficulty="easy",
        response_length="concise",
        interviewer_persona="friendly",
        prompt_technique="zero_shot",
        llm_model="openai/gpt-5-nano",
    )

    # Create a guest session
    result = create_session(config, user_id=None)
    session_id: UUID = result.session.id
    guest_token: str | None = result.session.guest_token
    assert guest_token is not None, "Guest session must have a token"

    # Use a random UUID as the "new user" (won't exist in auth.users, but DB UPDATE still works)
    fake_user_id = uuid4()
    migrated = migrate_guest_sessions(fake_user_id, [guest_token])

    assert session_id in migrated, "Session should appear in migrated list"

    # Verify via service client that guest_token is now NULL
    svc = get_service_client()
    row = (
        svc.table("sessions")
        .select("user_id, guest_token")
        .eq("id", str(session_id))
        .single()
        .execute()
    )
    assert row.data["guest_token"] is None, "guest_token should be cleared after migration"
    assert row.data["user_id"] == str(fake_user_id), "user_id should be set to new user"

    # Cleanup
    svc.table("sessions").delete().eq("id", str(session_id)).execute()
