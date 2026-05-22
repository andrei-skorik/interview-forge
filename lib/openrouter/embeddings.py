import streamlit as st

from lib.openrouter.client import OpenRouterClient


@st.cache_resource
def _get_client() -> OpenRouterClient:
    return OpenRouterClient()


async def get_embedding(text: str, model: str = "qwen/qwen3-embedding-8b") -> list[float]:
    """Get 4096-dim embedding for text via OpenRouter."""
    client: OpenRouterClient = _get_client()
    return await client.get_embeddings(text, model=model)
