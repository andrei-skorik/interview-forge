import asyncio
from typing import Any

import httpx
import streamlit as st
import structlog

from lib.exceptions import LLMProviderError, LLMTimeoutError

logger = structlog.get_logger(__name__)


class OpenRouterClient:
    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self) -> None:
        self._api_key: str = st.secrets["OPENROUTER_API_KEY"]
        self._app_url: str = st.secrets.get("APP_URL", "https://interviewforge.streamlit.app")

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "HTTP-Referer": self._app_url,
            "X-Title": "InterviewForge",
            "Content-Type": "application/json",
        }

    async def chat_complete(self, **params: Any) -> dict[str, Any]:
        timeout = httpx.Timeout(30.0)
        last_exc: Exception | None = None

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        f"{self.BASE_URL}/chat/completions",
                        json=params,
                        headers=self._headers,
                    )
                    if response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", "5"))
                        if attempt < 1:
                            await asyncio.sleep(retry_after)
                            continue
                        raise LLMProviderError("OpenRouter rate limit")
                    if response.status_code >= 500:
                        if attempt < 2:
                            await asyncio.sleep(2**attempt)
                            continue
                        raise LLMProviderError(f"OpenRouter {response.status_code}")
                    response.raise_for_status()
                    return response.json()  # type: ignore[no-any-return]
            except httpx.TimeoutException as exc:
                last_exc = exc
                if attempt < 2:
                    continue
        raise LLMTimeoutError("OpenRouter timeout after retries") from last_exc

    async def get_embeddings(
        self, text: str, model: str = "qwen/qwen3-embedding-8b"
    ) -> list[float]:
        timeout = httpx.Timeout(60.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.BASE_URL}/embeddings",
                json={"model": model, "input": text},
                headers=self._headers,
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            result: list[float] = data["data"][0]["embedding"]
            return result

    def get_models(self) -> dict[str, Any]:
        """Sync fetch of models list (used in scripts, not in Streamlit context)."""
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(
                f"{self.BASE_URL}/models",
                headers=self._headers,
            )
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
