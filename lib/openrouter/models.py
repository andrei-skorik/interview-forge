from datetime import datetime
from math import ceil

import streamlit as st
import structlog

from lib.schemas.api import ExchangeRate, ModelPricing, ModelsPricing

logger = structlog.get_logger(__name__)

TARGET_MODELS = {"openai/gpt-5-mini", "openai/gpt-5-nano"}

MODEL_DISPLAY_NAMES = {
    "openai/gpt-5-mini": "GPT-5 Mini",
    "openai/gpt-5-nano": "GPT-5 Nano",
}

MODEL_DESCRIPTIONS = {
    "openai/gpt-5-mini": "Best quality. Recommended for most interviews.",
    "openai/gpt-5-nano": "Faster and cheaper. Good for quick practice.",
}


@st.cache_data(ttl=3600)
def get_models_pricing() -> ModelsPricing:
    """Fetch model pricing from Supabase cache. TTL=1hr."""
    from supabase import create_client

    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])

    pricing_resp = supabase.table("model_pricing_cache").select("*").eq("is_active", True).execute()
    rate_resp = (
        supabase.table("currency_rates")
        .select("*")
        .eq("base", "USD")
        .eq("target", "EUR")
        .order("fetched_at", desc=True)
        .limit(1)
        .execute()
    )

    rate = 0.92
    rate_date = datetime.utcnow()
    rate_source = "fallback"
    if rate_resp.data:
        rate = float(rate_resp.data[0]["rate"])
        rate_date = datetime.fromisoformat(rate_resp.data[0]["fetched_at"])
        rate_source = "ecb"

    exchange_rate = ExchangeRate(
        base="USD", target="EUR", rate=rate, fetched_at=rate_date, source=rate_source
    )

    models: list[ModelPricing] = []
    for row in pricing_resp.data or []:
        if row["model_id"] not in TARGET_MODELS:
            continue
        prompt_price = float(row["prompt_price_per_million_usd"])
        completion_price = float(row["completion_price_per_million_usd"])
        # Estimate: typical session = 20K input + 4K output tokens
        # (system prompt ~1K × 10 turns + growing history, ~300 tokens output × 10 turns)
        typical_usd = (20_000 / 1_000_000) * prompt_price + (4_000 / 1_000_000) * completion_price
        est_eur_cents = ceil(typical_usd * 100 * rate)

        models.append(
            ModelPricing(
                id=row["model_id"],
                display_name=MODEL_DISPLAY_NAMES.get(row["model_id"], row["model_id"]),
                description=MODEL_DESCRIPTIONS.get(row["model_id"], ""),
                prompt_price_per_million_usd=prompt_price,
                completion_price_per_million_usd=completion_price,
                context_length=int(row["context_length"]),
                estimated_session_cost_eur_cents=est_eur_cents,
                is_recommended=(row["model_id"] == "openai/gpt-5-mini"),
            )
        )

    return ModelsPricing(
        models=models,
        exchange_rate=exchange_rate,
        pricing_fetched_at=datetime.utcnow(),
    )
