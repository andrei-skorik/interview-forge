"""GDPR cascade delete tests (Article 17 — Right to Erasure).

Integration tests — skip without SUPABASE_URL.
"""

import os
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("SUPABASE_URL"),
    reason="Requires SUPABASE_URL",
)


@pytest.fixture
def service_client():
    """Return Supabase service-role client."""
    from lib.db.client import get_service_client

    return get_service_client()


def test_delete_account_cascades_sessions_and_messages(service_client) -> None:
    """Deleting a user must cascade-delete sessions and their messages.

    Verifies GDPR Article 17 (Right to Erasure).
    """
    from lib.auth.gdpr import delete_account

    user_id = str(uuid4())
    email = f"test_{user_id[:8]}@test-gdpr.example.com"
    session_id = str(uuid4())
    message_id = str(uuid4())

    # Setup: insert session and message as if they belonged to user
    service_client.table("sessions").insert(
        {
            "id": session_id,
            "user_id": user_id,
            "status": "completed",
            "domain": "backend",
            "difficulty": "medium",
            "interviewer_persona": "neutral",
            "prompt_technique": "zero_shot",
            "llm_model": "openai/gpt-5-mini",
            "temperature": 0.7,
            "top_p": 1.0,
            "max_tokens": 1024,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "total_input_tokens": 10,
            "total_output_tokens": 20,
            "total_cost_usd_cents": 1,
            "share_enabled": False,
        }
    ).execute()

    service_client.table("messages").insert(
        {
            "id": message_id,
            "session_id": session_id,
            "role": "user",
            "content": "Test message for GDPR delete.",
            "sequence_number": 1,
            "suspicious": False,
            "metadata": {},
        }
    ).execute()

    # Act: delete account
    result = delete_account(user_id=user_id, email=email)

    # Assert: DeleteResult returned
    assert result.deleted is True

    # Assert: sessions deleted
    sessions = service_client.table("sessions").select("id").eq("user_id", user_id).execute()
    assert sessions.data == [], "Sessions must be deleted after account deletion"

    # Assert: messages deleted (via CASCADE)
    messages = service_client.table("messages").select("id").eq("session_id", session_id).execute()
    assert messages.data == [], "Messages must be cascade-deleted with session"


def test_delete_account_audit_log_entry_exists(service_client) -> None:
    """After deletion, audit_log must have an 'account_deleted' entry."""
    from lib.auth.gdpr import delete_account
    from lib.utils.ip_hash import hash_user_id

    user_id = str(uuid4())
    email = f"test_{user_id[:8]}@test-gdpr.example.com"

    delete_account(user_id=user_id, email=email)

    anonymized = hash_user_id(user_id)

    audit_rows = (
        service_client.table("audit_log")
        .select("action, anonymized_user_id")
        .eq("anonymized_user_id", anonymized)
        .eq("action", "account_deleted")
        .execute()
    )
    assert len(audit_rows.data) >= 1, "audit_log must record account_deleted action"


def test_delete_account_audit_log_has_no_raw_pii(service_client) -> None:
    """audit_log entry must NOT contain raw user_id or email."""
    from lib.auth.gdpr import delete_account

    user_id = str(uuid4())
    email = f"test_{user_id[:8]}@test-gdpr.example.com"

    delete_account(user_id=user_id, email=email)

    # Fetch all recent audit_log entries
    all_rows = (
        service_client.table("audit_log")
        .select("*")
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )

    for row in all_rows.data:
        row_str = str(row)
        assert user_id not in row_str, "Raw user_id must not appear in audit_log"
        assert email not in row_str, "Raw email must not appear in audit_log"


def test_delete_account_embeddings_deleted(service_client) -> None:
    """question_embeddings for the user must be deleted on account deletion."""
    from lib.auth.gdpr import delete_account

    user_id = str(uuid4())
    email = f"test_{user_id[:8]}@test-gdpr.example.com"
    session_id = str(uuid4())
    message_id = str(uuid4())

    # Setup session
    service_client.table("sessions").insert(
        {
            "id": session_id,
            "user_id": user_id,
            "status": "completed",
            "domain": "backend",
            "difficulty": "medium",
            "interviewer_persona": "neutral",
            "prompt_technique": "zero_shot",
            "llm_model": "openai/gpt-5-mini",
            "temperature": 0.7,
            "top_p": 1.0,
            "max_tokens": 1024,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd_cents": 0,
            "share_enabled": False,
        }
    ).execute()

    # Insert a fake embedding (all zeros — avoids needing a real model call)
    service_client.table("question_embeddings").insert(
        {
            "user_id": user_id,
            "session_id": session_id,
            "message_id": message_id,
            "question_text": "Test question for embedding.",
            "embedding": [0.0] * 4096,
            "domain": "backend",
        }
    ).execute()

    # Act
    delete_account(user_id=user_id, email=email)

    # Assert: embeddings deleted
    embeddings = (
        service_client.table("question_embeddings").select("id").eq("user_id", user_id).execute()
    )
    assert embeddings.data == [], "Embeddings must be deleted on account deletion"
