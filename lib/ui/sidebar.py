from __future__ import annotations

from typing import Any

import streamlit as st

from lib.openrouter.cost_calculator import format_eur
from lib.openrouter.models import get_models_pricing
from lib.prompts.interviewer.role_playing import PERSONA_AVATARS, PERSONA_NAMES


def render_session_config_sidebar() -> None:
    """Render interview configuration controls. Saves to st.session_state.session_config_form."""
    st.subheader("Interview Settings")

    st.caption(
        "🤖 **Domain is auto-detected from your job description** — "
        "the interviewer will ask questions relevant to the actual role."
    )

    difficulty = st.select_slider(
        "Difficulty",
        options=["easy", "medium", "hard"],
        value="medium",
        key="cfg_difficulty",
    )

    response_length = st.radio(
        "Question length",
        options=["concise", "detailed"],
        captions=["Short, direct (1–2 sentences)", "With context (2–5 sentences)"],
        horizontal=True,
        key="cfg_response_length",
        help="Applies to Zero Shot, Few Shot and Role Playing only. "
        "Chain of Thought and Structured Output are not affected.",
    )

    st.subheader("Interviewer")

    persona = st.radio(
        "Persona",
        options=["strict", "neutral", "friendly"],
        captions=[
            "Marcus Weber — Principal Engineer, Berlin",
            "Sarah Chen — Staff Engineer, Dublin",
            "Alex Rossi — Tech Lead, Amsterdam",
        ],
        key="cfg_persona",
    )

    prompt_technique = st.selectbox(
        "Prompt technique",
        options=["zero_shot", "few_shot", "chain_of_thought", "role_playing", "structured_output"],
        index=3,
        format_func=lambda x: x.replace("_", " ").title(),
        help="How the AI interviewer generates questions",
        key="cfg_prompt_technique",
    )

    with st.expander("⚙️ Model settings"):
        pricing_by_id: dict = {}
        try:
            pricing = get_models_pricing()
            model_options = [m.id for m in pricing.models]
            model_labels = {
                m.id: f"{m.display_name} (~{format_eur(m.estimated_session_cost_eur_cents)}/session)"
                for m in pricing.models
            }
            pricing_by_id = {m.id: m for m in pricing.models}
        except Exception:
            model_options = ["openai/gpt-5-mini", "openai/gpt-5-nano"]
            model_labels = {
                "openai/gpt-5-mini": "GPT-5 Mini (~€0.05/session)",
                "openai/gpt-5-nano": "GPT-5 Nano (~€0.02/session)",
            }

        llm_model = st.selectbox(
            "Model",
            options=model_options,
            format_func=lambda x: model_labels.get(x, x),
            key="cfg_llm_model",
        )
        if llm_model in pricing_by_id:
            m = pricing_by_id[llm_model]
            st.caption(
                f"${m.prompt_price_per_million_usd:.3f} input · "
                f"${m.completion_price_per_million_usd:.3f} output per M tokens"
            )
        if "nano" in llm_model:
            st.caption(
                "⚠️ GPT-nano is fast and cheap, but prompt techniques "
                "(Few Shot, Chain of Thought, Role Playing) have limited effect — "
                "the model lacks capacity to follow nuanced instructions. "
                "Use **GPT-mini** for best interview quality."
            )
        temperature = st.slider("Temperature", 0.0, 1.5, 0.7, 0.05, key="cfg_temperature")
        max_tokens = st.slider("Max tokens", 256, 4096, 2048, 128, key="cfg_max_tokens")

        with st.expander("🔬 Advanced"):
            top_p = st.slider("Top P", 0.0, 1.0, 1.0, 0.05, key="cfg_top_p")
            frequency_penalty = st.slider(
                "Frequency penalty", -2.0, 2.0, 0.0, 0.1, key="cfg_freq_penalty"
            )
            presence_penalty = st.slider(
                "Presence penalty", -2.0, 2.0, 0.0, 0.1, key="cfg_pres_penalty"
            )

    st.session_state["session_config_form"] = {
        # domain is intentionally omitted — auto-detected from JD in create_session()
        "difficulty": difficulty,
        "response_length": response_length,
        "interviewer_persona": persona,
        "prompt_technique": prompt_technique,
        "llm_model": llm_model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p,
        "frequency_penalty": frequency_penalty,
        "presence_penalty": presence_penalty,
    }


MIN_QUESTIONS_TO_END = 3


def render_interview_sidebar(session_id: str, session_data: dict[str, Any]) -> bool:
    """Render sidebar during active interview. Returns True if user clicked End interview."""
    persona = session_data.get("persona", "neutral")
    avatar = PERSONA_AVATARS.get(persona, "🤖")
    name = PERSONA_NAMES.get(persona, "AI Interviewer")

    st.markdown(f"### {avatar} {name}")
    st.caption(f"Persona: {persona.title()}")

    cost_cents = session_data.get("total_cost_usd_cents", 0)
    message_count = session_data.get("message_count", 0)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Cost", format_eur(cost_cents))
    with col2:
        st.metric("Q&A", message_count)

    st.divider()

    can_end = message_count >= MIN_QUESTIONS_TO_END
    if not can_end:
        remaining = MIN_QUESTIONS_TO_END - message_count
        st.info(
            f"Answer **{remaining} more question{'s' if remaining > 1 else ''}** "
            f"to finish ({message_count}/{MIN_QUESTIONS_TO_END} done).",
            icon="ℹ️",
        )

    end_clicked: bool = st.button(
        "⏹️ End interview",
        type="primary",
        use_container_width=True,
        disabled=not can_end,
        key="end_interview_btn",
    )
    return end_clicked
