from xml.etree import ElementTree as ET

import httpx
import structlog

logger = structlog.get_logger(__name__)

ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
ECB_NS = {
    "gesmes": "http://www.gesmes.org/xml/2002-08-01",
    "ecb": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref",
}


async def fetch_usd_eur_rate() -> float:
    """Fetch current USD→EUR rate from European Central Bank XML feed."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        response = await client.get(ECB_URL)
        response.raise_for_status()
        root = ET.fromstring(response.content)

    for cube in root.findall(".//ecb:Cube[@currency]", ECB_NS):
        if cube.attrib.get("currency") == "USD":
            usd_per_eur = float(cube.attrib["rate"])
            return 1.0 / usd_per_eur

    raise ValueError("USD rate not found in ECB response")
