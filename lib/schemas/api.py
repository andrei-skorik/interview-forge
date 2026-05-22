from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ModelPricing(BaseModel):
    id: str
    display_name: str
    description: str
    prompt_price_per_million_usd: float
    completion_price_per_million_usd: float
    context_length: int
    estimated_session_cost_eur_cents: int
    is_recommended: bool


class ExchangeRate(BaseModel):
    base: str
    target: str
    rate: float
    fetched_at: datetime
    source: str


class ModelsPricing(BaseModel):
    models: list[ModelPricing]
    exchange_rate: ExchangeRate
    pricing_fetched_at: datetime


class CostBreakdown(BaseModel):
    usd_cents: int
    eur_cents: int
    input_tokens: int
    output_tokens: int
