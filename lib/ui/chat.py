from __future__ import annotations

import streamlit as st

from lib.prompts.interviewer.role_playing import PERSONA_AVATARS
from lib.schemas.messages import Message


def render_chat_history(messages: list[Message], persona: str = "neutral") -> None:
    """Render full chat history. System messages are skipped."""
    for msg in messages:
        if msg.role == "system":
            continue
        avatar = PERSONA_AVATARS.get(persona, "🤖") if msg.role == "assistant" else "🧑"

        with st.chat_message(msg.role, avatar=avatar):
            st.markdown(msg.content)


def render_typing_indicator() -> None:
    """Show a 'Thinking...' placeholder while the LLM is generating."""
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown("*Thinking...*")
