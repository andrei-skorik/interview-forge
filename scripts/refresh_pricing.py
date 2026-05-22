#!/usr/bin/env python3
"""Refresh model pricing cache from OpenRouter. Run hourly via GitHub Actions."""

import asyncio
import os
import sys
from datetime import datetime

import httpx
import structlog

from supabase import Client, create_client

logger = structlog.get_logger(__name__)

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
TARGET_MODELS: set[str] = {"openai/gpt-5-mini", "openai/gpt-5-nano"}


async def fetch_openrouter_models(api_key: str) -> list[dict]:
    """Fetch all models from OpenRouter /models endpoint."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://interviewforge.streamlit.app",
        "X-Title": "InterviewForge",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(OPENROUTER_MODELS_URL, headers=headers)
        response.raise_for_status()
        data: list[dict] = response.json()["data"]
        return data


def upsert_model_pricing(supabase_client: Client, models: list[dict]) -> int:
    """Upsert filtered models into model_pricing_cache. Returns count of upserted rows."""
    count = 0
    for model in models:
        model_id: str = model.get("id", "")
        if model_id not in TARGET_MODELS:
            continue
        pricing: dict = model.get("pricing", {})
        row: dict = {
            "model_id": model_id,
            "prompt_price_per_million_usd": float(pricing.get("prompt", 0)) * 1_000_000,
            "completion_price_per_million_usd": float(pricing.get("completion", 0)) * 1_000_000,
            "context_length": model.get("context_length", 0),
            "is_active": True,
            "raw_response": model,
            "fetched_at": datetime.utcnow().isoformat(),
        }
        supabase_client.table("model_pricing_cache").upsert(row, on_conflict="model_id").execute()
        count += 1
        logger.info("upserted_model", model_id=model_id)
    return count


def main() -> None:
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")

    if not all([supabase_url, supabase_key, openrouter_key]):
        logger.error(
            "missing_env_vars",
            required=["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "OPENROUTER_API_KEY"],
        )
        sys.exit(1)

    # Type narrowing: all checked above
    assert supabase_url is not None
    assert supabase_key is not None
    assert openrouter_key is not None

    supabase = create_client(supabase_url, supabase_key)
    models = asyncio.run(fetch_openrouter_models(openrouter_key))
    count = upsert_model_pricing(supabase, models)
    logger.info("pricing_refresh_complete", models_upserted=count)


if __name__ == "__main__":
    structlog.configure(processors=[structlog.dev.ConsoleRenderer()])
    main()
