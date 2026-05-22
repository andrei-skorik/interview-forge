#!/usr/bin/env python3
"""Refresh USD/EUR exchange rate from ECB. Run daily 9am UTC via GitHub Actions."""

import os
import sys
from datetime import datetime
from xml.etree import ElementTree

import httpx
import structlog

from supabase import Client, create_client

logger = structlog.get_logger(__name__)

ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
ECB_NS = "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"


def fetch_usd_eur_rate() -> float:
    """Fetch current USD rate from ECB XML. Returns USD→EUR rate (how many EUR per 1 USD).

    ECB publishes rates with EUR as base, so the XML gives USD-per-EUR.
    We invert to get EUR-per-USD (i.e. how many EUR you get for 1 USD).
    """
    response = httpx.get(ECB_URL, timeout=30.0)
    response.raise_for_status()

    root = ElementTree.fromstring(response.text)

    for cube in root.iter(f"{{{ECB_NS}}}Cube"):
        if cube.get("currency") == "USD":
            rate_str = cube.get("rate")
            if rate_str is None:
                raise ValueError("USD Cube element has no 'rate' attribute")
            usd_per_eur = float(rate_str)
            return 1.0 / usd_per_eur  # Convert to USD→EUR rate

    raise ValueError("USD rate not found in ECB XML")


def store_currency_rate(supabase_client: Client, rate: float) -> None:
    """Insert the USD→EUR rate into the currency_rates table."""
    row: dict = {
        "base": "USD",
        "target": "EUR",
        "rate": rate,
        "fetched_at": datetime.utcnow().isoformat(),
    }
    supabase_client.table("currency_rates").insert(row).execute()


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
        rate = fetch_usd_eur_rate()
    except (httpx.HTTPError, ValueError, ElementTree.ParseError) as exc:
        logger.error("fetch_rate_failed", error=str(exc))
        sys.exit(1)

    store_currency_rate(supabase, rate)
    logger.info("currency_refresh_complete", usd_to_eur=rate)


if __name__ == "__main__":
    structlog.configure(processors=[structlog.dev.ConsoleRenderer()])
    main()
