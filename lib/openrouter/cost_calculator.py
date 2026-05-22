from math import ceil

from lib.schemas.api import CostBreakdown, ModelPricing


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    model_pricing: ModelPricing,
    usd_to_eur_rate: float,
) -> CostBreakdown:
    """Calculate cost in integer cents. Always ceil — never undercount."""
    input_cost_usd = (input_tokens / 1_000_000) * model_pricing.prompt_price_per_million_usd
    output_cost_usd = (output_tokens / 1_000_000) * model_pricing.completion_price_per_million_usd
    total_usd = input_cost_usd + output_cost_usd
    usd_cents = ceil(total_usd * 100)
    eur_cents = ceil(usd_cents * usd_to_eur_rate)
    return CostBreakdown(
        usd_cents=usd_cents,
        eur_cents=eur_cents,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def format_eur(cents: int) -> str:
    if cents == 0:
        return "€0.00"
    if cents < 1:
        return "< €0.01"
    return f"€{cents / 100:.2f}"


def format_usd(cents: int) -> str:
    if cents == 0:
        return "$0.00"
    if cents < 1:
        return "< $0.01"
    return f"${cents / 100:.2f}"
