"""Shared pytest fixtures for InterviewForge tests."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from lib.schemas.jd_analysis import JDAnalysis
from lib.schemas.messages import Message
from lib.schemas.session import SessionConfig

# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def sample_jd() -> str:
    return (
        "We are looking for a Senior Python Backend Engineer to join our Berlin-based fintech startup. "
        "You will build REST APIs with FastAPI, work with PostgreSQL and Redis, deploy on AWS with "
        "Docker/Kubernetes. Must have 5+ years Python experience, strong knowledge of async programming, "
        "SQL optimization. Experience with Pydantic v2, pytest, mypy, CI/CD pipelines required."
    )


@pytest.fixture
def sample_jd_analysis() -> JDAnalysis:
    return JDAnalysis(
        stack=["Python", "FastAPI", "PostgreSQL", "Redis", "AWS", "Docker"],
        level="senior",
        suggested_domain="backend",
        key_topics=["async programming", "SQL optimization", "REST APIs", "CI/CD"],
        company_type="tech_startup",
        confidence=0.92,
    )


@pytest.fixture
def sample_session_config(sample_jd: str) -> SessionConfig:
    return SessionConfig(
        job_description=sample_jd,
        domain="backend",
        difficulty="medium",
        response_length="detailed",
        interviewer_persona="neutral",
        prompt_technique="role_playing",
        llm_model="openai/gpt-5-mini",
        temperature=0.7,
        max_tokens=1024,
    )


@pytest.fixture
def sample_messages() -> list[Message]:
    session_id = uuid4()
    return [
        Message(
            id=uuid4(),
            session_id=session_id,
            role="assistant",
            content="Tell me about your experience with async Python.",
            sequence_number=1,
            input_tokens=None,
            output_tokens=None,
            cost_usd_cents=None,
            latency_ms=None,
            suspicious=False,
            metadata={},
            created_at=datetime.utcnow(),
        ),
        Message(
            id=uuid4(),
            session_id=session_id,
            role="user",
            content="I have 3 years of experience with asyncio and have built high-throughput APIs using FastAPI.",
            sequence_number=2,
            input_tokens=None,
            output_tokens=None,
            cost_usd_cents=None,
            latency_ms=None,
            suspicious=False,
            metadata={},
            created_at=datetime.utcnow(),
        ),
        Message(
            id=uuid4(),
            session_id=session_id,
            role="assistant",
            content="How do you handle database connection pooling in async context?",
            sequence_number=3,
            input_tokens=None,
            output_tokens=None,
            cost_usd_cents=None,
            latency_ms=None,
            suspicious=False,
            metadata={},
            created_at=datetime.utcnow(),
        ),
        Message(
            id=uuid4(),
            session_id=session_id,
            role="user",
            content="I use SQLAlchemy async with asyncpg driver and configure pool_size based on expected concurrency.",
            sequence_number=4,
            input_tokens=None,
            output_tokens=None,
            cost_usd_cents=None,
            latency_ms=None,
            suspicious=False,
            metadata={},
            created_at=datetime.utcnow(),
        ),
        Message(
            id=uuid4(),
            session_id=session_id,
            role="assistant",
            content="Describe a time you optimized a slow SQL query.",
            sequence_number=5,
            input_tokens=None,
            output_tokens=None,
            cost_usd_cents=None,
            latency_ms=None,
            suspicious=False,
            metadata={},
            created_at=datetime.utcnow(),
        ),
        Message(
            id=uuid4(),
            session_id=session_id,
            role="user",
            content="I used EXPLAIN ANALYZE to find missing indexes and rewrote a N+1 query to use JOINs, reducing latency by 80%.",
            sequence_number=6,
            input_tokens=None,
            output_tokens=None,
            cost_usd_cents=None,
            latency_ms=None,
            suspicious=False,
            metadata={},
            created_at=datetime.utcnow(),
        ),
    ]


@pytest.fixture
def mock_openrouter_client() -> AsyncMock:
    """Mock OpenRouterClient to prevent real API calls."""
    mock = AsyncMock()
    mock.chat_complete.return_value = {
        "choices": [
            {
                "message": {
                    "content": "What is the difference between async and threading in Python?"
                }
            }
        ],
        "usage": {"prompt_tokens": 150, "completion_tokens": 30},
    }
    return mock


@pytest.fixture
def mock_supabase() -> MagicMock:
    """Mock supabase client."""
    mock = MagicMock()
    mock.table.return_value.select.return_value.execute.return_value.data = []
    mock.table.return_value.insert.return_value.execute.return_value.data = [{"id": str(uuid4())}]
    return mock
