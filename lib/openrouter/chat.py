import re
from typing import Any

import streamlit as st
import structlog

from lib.openrouter.client import OpenRouterClient

logger = structlog.get_logger(__name__)


@st.cache_resource
def get_openrouter_client() -> OpenRouterClient:
    return OpenRouterClient()


async def chat_complete(
    model: str,
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    top_p: float = 1.0,
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0,
    response_format: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Wrapper around OpenRouterClient.chat_complete with logging."""
    client: OpenRouterClient = get_openrouter_client()
    params: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p,
        "frequency_penalty": frequency_penalty,
        "presence_penalty": presence_penalty,
    }
    if response_format:
        params["response_format"] = response_format

    result = await client.chat_complete(**params)

    usage = result.get("usage", {})
    logger.info(
        "openrouter_chat_complete",
        model=model,
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
    )
    return result


def extract_question_from_cot(response_text: str) -> str:
    """Extract <question>...</question> from CoT response. Falls back to full text."""
    match = re.search(r"<question>(.*?)</question>", response_text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return response_text.strip()


def get_message_content(response: dict[str, Any]) -> str:
    """Extract content string from OpenRouter chat response."""
    return str(response["choices"][0]["message"]["content"])


def get_usage(response: dict[str, Any]) -> tuple[int, int]:
    """Return (prompt_tokens, completion_tokens) from response."""
    usage = response.get("usage", {})
    return int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))
