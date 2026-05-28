import streamlit as st

import datetime as dt  # noqa: E402
from uuid import UUID  # noqa: E402
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError  # noqa: E402

from lib.auth.session import (  # noqa: E402
    clear_session,
    get_access_token,
    get_current_user_id,
    is_authenticated,
)
from lib.db.sessions import list_user_sessions  # noqa: E402
from lib.openrouter.cost_calculator import format_eur  # noqa: E402
from lib.schemas.session import SessionFilters  # noqa: E402

# ── Timezone helpers ───────────────────────────────────────────────────────────
_TIMEZONE_OPTIONS: dict[str, str] = {
    "UTC (UTC+0)": "UTC",
    "London (UTC+0/+1)": "Europe/London",
    "Berlin / Paris / Warsaw (UTC+1/+2)": "Europe/Berlin",
    "Helsinki / Tallinn / Riga (UTC+2/+3)": "Europe/Helsinki",
    "Moscow (UTC+3)": "Europe/Moscow",
}
_UTC = ZoneInfo("UTC")


def _fmt_local(ts: dt.datetime, tz: ZoneInfo) -> str:
    """Convert a UTC (or naive) datetime to local timezone for display."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=_UTC)
    return ts.astimezone(tz).strftime("%Y-%m-%d %H:%M")


if not is_authenticated():
    st.warning("Please sign in to view your dashboard.")
    if st.button("← Go to home"):
        st.switch_page("app.py")
    st.stop()

user_id: UUID = get_current_user_id()  # type: ignore[assignment]
access_token: str = get_access_token() or ""

# ── Sidebar filters ────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("Filters")

    domain_options = ["frontend", "backend", "data_ml", "devops", "system_design", "behavioral"]
    selected_domains: list[str] = st.multiselect(
        "Domain",
        options=domain_options,
        format_func=lambda x: x.replace("_", " ").title(),
        default=[],
    )

    status_options = [
        "in_progress",
        "evaluating",
        "completed",
        "completed_without_eval",
        "abandoned",
    ]
    selected_status: str | None = st.selectbox(
        "Status",
        options=["(all)"] + status_options,
        format_func=lambda x: x.replace("_", " ").title() if x != "(all)" else "All statuses",
    )
    if selected_status == "(all)":
        selected_status = None

    date_range = st.date_input("Date range", value=(), key="date_range")
    date_from = None
    date_to = None
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        date_from = dt.datetime.combine(date_range[0], dt.time.min)
        date_to = dt.datetime.combine(date_range[1], dt.time.max)

    st.divider()
    tz_label: str = st.selectbox(
        "Timezone",
        options=list(_TIMEZONE_OPTIONS.keys()),
        index=2,  # default: Berlin / Paris / Warsaw (UTC+1/+2)
        key="dashboard_tz",
        help="All times are stored in UTC. Select your local timezone to convert them.",
    )  # type: ignore[assignment]
    try:
        _user_tz = ZoneInfo(_TIMEZONE_OPTIONS[tz_label])
    except ZoneInfoNotFoundError:
        _user_tz = _UTC

    page_num: int = st.session_state.get("dashboard_page", 1)

# ── Load sessions ──────────────────────────────────────────────────────────────
try:
    filters = SessionFilters(
        domains=selected_domains,
        status=selected_status,
        date_from=date_from,
        date_to=date_to,
    )
    sessions_list = list_user_sessions(
        user_id,
        access_token,
        page=page_num,
        per_page=20,
        filters=filters,
    )
except Exception as exc:
    err_str = str(exc)
    if "JWT expired" in err_str or "PGRST303" in err_str or "token is expired" in err_str.lower():
        st.warning("⏱️ Your session has expired. Please sign in again.")
        clear_session()
        if st.button("🔑 Sign in", type="primary"):
            st.switch_page("app.py")
    else:
        st.error(f"Could not load sessions: {exc}")
    st.stop()

# ── Top metrics ────────────────────────────────────────────────────────────────
st.title("📊 Your Interview Dashboard")

completed = [
    s for s in sessions_list.sessions if s.status in ("completed", "completed_without_eval")
]
total_cost = sum(s.total_cost_usd_cents for s in sessions_list.sessions)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Sessions", sessions_list.total)
m2.metric("Completed", len(completed))
m3.metric("Total Cost", format_eur(total_cost))

# Best domain by session count
if sessions_list.sessions:
    domain_counts: dict[str, int] = {}
    for s in sessions_list.sessions:
        domain_counts[s.domain] = domain_counts.get(s.domain, 0) + 1
    best_domain = max(domain_counts, key=lambda k: domain_counts[k])
    m4.metric("Most Practiced", best_domain.replace("_", " ").title())
else:
    m4.metric("Most Practiced", "—")

st.divider()

# ── Session list ───────────────────────────────────────────────────────────────
if not sessions_list.sessions:
    st.info("No sessions yet. Start your first interview!")
    if st.button("→ Start interview"):
        st.switch_page("app.py")
else:
    status_badge_map = {
        "completed": "✅",
        "completed_without_eval": "✅",
        "in_progress": "🔄",
        "evaluating": "⏳",
        "abandoned": "❌",
    }

    for session in sessions_list.sessions:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                jd_preview = (session.domain or "").replace("_", " ").title()
                st.markdown(
                    f"**{jd_preview}** — {session.difficulty.title()} · {session.prompt_technique.replace('_', ' ').title()}"
                )
                st.caption(_fmt_local(session.created_at, _user_tz))
            with col2:
                badge = status_badge_map.get(session.status, "❓")
                st.markdown(f"{badge} {session.status.replace('_', ' ').title()}")
            with col3:
                st.caption(format_eur(session.total_cost_usd_cents))
            with col4:
                if session.status in ("completed", "completed_without_eval") and st.button(
                    "View report", key=f"view_{session.id}"
                ):
                    st.session_state["view_session_id"] = str(session.id)
                    st.switch_page("pages/6_📈_Report.py")
        st.divider()

# ── Pagination ─────────────────────────────────────────────────────────────────
total_pages = max(1, (sessions_list.total + 19) // 20)
if total_pages > 1:
    pcol1, pcol2, pcol3 = st.columns([1, 2, 1])
    with pcol1:
        if page_num > 1 and st.button("← Previous"):
            st.session_state["dashboard_page"] = page_num - 1
            st.rerun()
    with pcol2:
        st.caption(f"Page {page_num} of {total_pages}")
    with pcol3:
        if page_num < total_pages and st.button("Next →"):
            st.session_state["dashboard_page"] = page_num + 1
            st.rerun()
