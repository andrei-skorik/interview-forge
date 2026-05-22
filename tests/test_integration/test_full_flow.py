"""E2E integration test: create session → 3 messages → finish → report.

Requires SUPABASE_URL + OPENROUTER_API_KEY env vars.
Costs ~€0.05 per run against real APIs.
"""

import os
from uuid import UUID

import pytest

pytestmark = pytest.mark.skipif(
    not (os.environ.get("SUPABASE_URL") and os.environ.get("OPENROUTER_API_KEY")),
    reason="E2E test requires SUPABASE_URL and OPENROUTER_API_KEY",
)

SAMPLE_JD = """
We are looking for a Senior Python Backend Engineer to join our Berlin fintech startup.
You will build REST APIs with FastAPI, work with PostgreSQL and Redis, deploy on AWS.
Must have 5+ years Python experience, strong async knowledge, SQL optimisation skills.
"""

SAMPLE_ANSWERS = [
    "I have 4 years of experience with asyncio. I've built high-throughput APIs with FastAPI and handled async DB access via asyncpg.",
    "For connection pooling I configure SQLAlchemy async engine with pool_size tuned to the expected concurrency.",
    "I used EXPLAIN ANALYZE to find missing composite indexes and rewrote N+1 queries with JOINs, cutting latency by 80%.",
]


@pytest.mark.integration
def test_full_interview_flow() -> None:
    """E2E: create session → 3 user messages → finish → valid report."""
    from lib.db.evaluations import get_report
    from lib.db.messages import send_message
    from lib.db.sessions import create_session, finish_interview
    from lib.schemas.judge import DetailedReport, SummaryReport
    from lib.schemas.session import SessionConfig

    config = SessionConfig(
        job_description=SAMPLE_JD,
        domain="backend",
        difficulty="medium",
        response_length="concise",
        interviewer_persona="neutral",
        prompt_technique="role_playing",
        llm_model="openai/gpt-5-mini",
    )

    result = create_session(config, user_id=None)
    session_id: UUID = result.session.id
    guest_token: str | None = result.session.guest_token

    assert result.first_message.content, "First message must not be empty"

    for answer in SAMPLE_ANSWERS:
        msg_result = send_message(session_id, answer, guest_token=guest_token)
        assert msg_result.assistant_message.content

    finish = finish_interview(session_id, guest_token=guest_token)
    assert finish.status in {"completed", "completed_without_eval"}
    assert finish.total_cost_usd_cents > 0

    report = get_report(session_id, guest_token=guest_token)
    assert report is not None

    # Validate both JSON formats
    DetailedReport.model_validate(report.detailed_json)
    SummaryReport.model_validate(report.summary_json)
