import streamlit as st

# MUST be the first Streamlit call
st.set_page_config(
    page_title="InterviewForge",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

from uuid import UUID  # noqa: E402

from lib.auth.login import restore_session  # noqa: E402
from lib.auth.session import (  # noqa: E402
    clear_session,
    get_access_token,
    get_current_user_id,
    get_refresh_token,
    is_authenticated,
    is_token_expired,
    set_session,
)
from lib.db.messages import get_messages_by_session, send_message  # noqa: E402
from lib.db.sessions import create_session, finish_interview, get_session  # noqa: E402
from lib.exceptions import (  # noqa: E402
    LLMProviderError,
    LLMTimeoutError,
    PromptInjectionError,
    RateLimitError,
    ValidationError,
)
from lib.prompts.interviewer.role_playing import PERSONA_AVATARS, PERSONA_NAMES  # noqa: E402
from lib.prompts.jd_analyzer import analyze_jd_cached  # noqa: E402
from lib.schemas.session import SessionConfig  # noqa: E402
from lib.ui.auth_widgets import login_form, register_form, render_account_widget  # noqa: E402
from lib.ui.chat import render_chat_history  # noqa: E402
from lib.ui.sidebar import render_interview_sidebar, render_session_config_sidebar  # noqa: E402
from lib.utils.logging import configure_logging  # noqa: E402

configure_logging()

# ── Session state initialisation ──────────────────────────────────────────────
if "active_sessions" not in st.session_state:
    st.session_state["active_sessions"] = {}
if "app_mode" not in st.session_state:
    st.session_state["app_mode"] = "landing"
if "current_session_id" not in st.session_state:
    st.session_state["current_session_id"] = None
if "session_config_form" not in st.session_state:
    st.session_state["session_config_form"] = {}

# Restore / refresh Supabase session on every page render.
# Covers two cases:
#   1. Page reload — session_state lost, need to restore from stored tokens
#   2. Token expired while user is still "authenticated" in session_state
if "supabase_session" in st.session_state and (not is_authenticated() or is_token_expired()):
    _stored = st.session_state["supabase_session"]
    try:
        _result = restore_session(
            _stored.get("access_token", ""),
            _stored.get("refresh_token", ""),
        )
        if _result:
            set_session(_result["session"], _result["user"])
        else:
            clear_session()
    except Exception:
        clear_session()


# ── Interview page ─────────────────────────────────────────────────────────────

def _interview_page() -> None:
    """Main interview page: landing → start interview → active chat."""

    if st.session_state["app_mode"] == "auth":
        with st.sidebar:
            render_account_widget()

        st.title("Welcome to InterviewForge 🎯")
        tab_login, tab_register = st.tabs(["Sign in", "Create account"])
        with tab_login:
            login_form()
        with tab_register:
            register_form()

    elif st.session_state["app_mode"] == "active_interview":
        session_id = st.session_state["current_session_id"]
        session_ref: dict = st.session_state["active_sessions"].get(session_id, {})

        with st.sidebar:
            access_token = get_access_token()
            guest_token: str | None = session_ref.get("guest_token")
            persona: str = session_ref.get("persona", "neutral")

            try:
                session_obj = get_session(
                    UUID(session_id),
                    access_token=access_token,
                    guest_token=guest_token,
                )
                user_msg_count = len([m for m in session_obj.messages if m.role == "user"])
                persona = session_obj.interviewer_persona
                end_clicked = render_interview_sidebar(
                    session_id,
                    {
                        "persona": persona,
                        "total_cost_usd_cents": session_obj.total_cost_usd_cents,
                        "message_count": user_msg_count,
                    },
                )
            except Exception:
                end_clicked = st.button(
                    "⏹️ End interview", type="primary", use_container_width=True
                )

            if end_clicked:
                with st.spinner("Generating your report..."):
                    try:
                        finish_interview(
                            UUID(session_id),
                            access_token=access_token,
                            guest_token=guest_token,
                        )
                        st.session_state["app_mode"] = "landing"
                        st.session_state["view_session_id"] = session_id
                        st.switch_page("pages/6_📈_Report.py")
                    except ValidationError as exc:
                        st.error(exc.detail or exc.user_message)
                    except Exception:
                        st.error("Could not generate report. Please try again.")

        persona_name = PERSONA_NAMES.get(persona, "AI Interviewer")
        st.title(f"🎯 Interview with {persona_name}")

        try:
            messages = get_messages_by_session(
                UUID(session_id),
                access_token=get_access_token(),
                guest_token=session_ref.get("guest_token"),
            )
            render_chat_history(messages, persona=persona)
        except Exception:
            st.error("Could not load messages.")
            st.stop()

        if user_input := st.chat_input("Type your answer..."):
            with st.chat_message("user", avatar="🧑"):
                st.markdown(user_input)

            with st.chat_message("assistant", avatar=PERSONA_AVATARS.get(persona, "🤖")):
                with st.spinner("Thinking..."):
                    try:
                        result = send_message(
                            UUID(session_id),
                            user_input,
                            access_token=get_access_token(),
                            guest_token=session_ref.get("guest_token"),
                        )
                        st.markdown(result.assistant_message.content)
                        st.rerun()
                    except PromptInjectionError:
                        st.error("⚠️ Your input contains patterns that violate our usage policy.")
                    except LLMTimeoutError:
                        st.error("⏱️ The AI took too long to respond. Please try again.")
                        if st.button("🔄 Retry", key="retry_msg"):
                            st.rerun()
                    except RateLimitError:
                        st.error("🚦 Too many requests. Please wait a moment.")
                    except LLMProviderError as exc:
                        st.error(f"Service error: {exc.user_message}")

    else:  # landing mode
        with st.sidebar:
            render_account_widget()
            st.divider()
            render_session_config_sidebar()

        col1, col2 = st.columns([2, 1])
        with col1:
            st.title("🎯 Practice EU tech interviews with AI")
            st.markdown("Get personalised questions and structured feedback in 20 minutes.")
        with col2:
            _user_id = get_current_user_id()
            if _user_id:
                try:
                    from lib.db.sessions import list_user_sessions

                    _sessions_list = list_user_sessions(_user_id, get_access_token() or "")
                    st.metric("Your sessions", _sessions_list.total)
                except Exception:
                    pass

        st.divider()

        jd = st.text_area(
            "Job Description",
            placeholder="Paste the job description here (min 50 characters)...",
            height=200,
            max_chars=10_000,
            help="The more detailed the JD, the better your interview questions will be",
            key="jd_input",
        )
        st.caption(f"{len(jd)}/10,000 characters · After pasting, press **Ctrl+Enter** to apply")

        start_disabled = not jd or len(jd) < 50
        if st.button(
            "🚀 Start interview",
            type="primary",
            disabled=start_disabled,
            use_container_width=False,
            key="start_interview",
        ):
            form_data: dict = st.session_state.get("session_config_form", {})
            try:
                config = SessionConfig(job_description=jd, **form_data)
            except Exception as exc:
                st.error(f"Invalid settings: {exc}")
                st.stop()

            with st.spinner("Preparing your interview..."):
                try:
                    result = create_session(config, user_id=get_current_user_id())

                    sid = str(result.session.id)
                    st.session_state["active_sessions"][sid] = {
                        "guest_token": result.session.guest_token,
                        "persona": config.interviewer_persona,
                    }
                    st.session_state["app_mode"] = "active_interview"
                    st.session_state["current_session_id"] = sid
                    st.rerun()
                except PromptInjectionError:
                    st.error(
                        "⚠️ Your job description contains patterns that violate our usage policy. "
                        "Please rewrite it."
                    )
                except RateLimitError:
                    st.error("🚦 Too many sessions started. Please wait a minute.")
                except LLMProviderError as exc:
                    st.error(f"Service temporarily unavailable: {exc.user_message}")
                except LLMTimeoutError:
                    st.error("⏱️ Took too long to start. Please try again.")

        # ── JD analysis preview (below the button so it never shifts button position) ──
        if jd and len(jd) >= 50:
            with st.expander("📊 Job analysis preview", expanded=False):
                with st.spinner("Analysing..."):
                    try:
                        analysis = analyze_jd_cached(jd)
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.metric("Level", analysis.level.title())
                            st.metric(
                                "Domain", analysis.suggested_domain.replace("_", " ").title()
                            )
                        with col_b:
                            st.markdown("**Stack detected:**")
                            for tech in analysis.stack[:5]:
                                st.badge(tech)
                    except Exception:
                        st.warning("Could not analyse JD preview.")


# ── Navigation ─────────────────────────────────────────────────────────────────
# Session state init and auth refresh (above) run on every page render.
# st.navigation dispatches to the selected page.

_pg = st.navigation(
    [
        st.Page(_interview_page, title="Interview", icon="🎤", default=True),
        st.Page("pages/1_📊_Dashboard.py", title="Dashboard", icon="📊"),
        st.Page("pages/2_⚙️_Settings.py", title="Settings", icon="⚙️"),
        st.Page("pages/3_🔒_Admin.py", title="Admin", icon="🔒"),
        st.Page("pages/4_📄_Privacy.py", title="Privacy", icon="📄"),
        st.Page("pages/5_📋_Terms.py", title="Terms", icon="📋"),
        st.Page("pages/6_📈_Report.py", title="Report", icon="📈"),
    ]
)
_pg.run()
