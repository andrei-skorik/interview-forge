import json

import streamlit as st

st.set_page_config(page_title="Interview Report", page_icon="📈", layout="wide")

from uuid import UUID  # noqa: E402

from lib.auth.session import clear_session, get_access_token, get_current_user_id  # noqa: E402
from lib.db.evaluations import get_full_report  # noqa: E402
from lib.ui.report import render_detailed, render_summary  # noqa: E402

# ── Read URL params ────────────────────────────────────────────────────────────
session_id_str: str | None = st.query_params.get("session_id")
share_token: str | None = st.query_params.get("share_token")

# Also accept session_id from session state (set when navigating from Dashboard or End interview)
if not session_id_str:
    session_id_str = (
        st.session_state.get("view_session_id")
        or st.session_state.get("current_session_id")
    )

if not session_id_str:
    st.info("Open a report from the Dashboard by clicking 'View report' on a completed session.")
    if st.button("→ Go to Dashboard"):
        st.switch_page("pages/1_📊_Dashboard.py")
    st.stop()

# ── Load report ────────────────────────────────────────────────────────────────
with st.spinner("Loading report..."):
    try:
        report = get_full_report(
            UUID(session_id_str),
            access_token=get_access_token(),
            share_token=share_token,
        )
    except Exception as exc:
        err_str = str(exc)
        if "JWT expired" in err_str or "PGRST303" in err_str or "token is expired" in err_str.lower():
            st.warning("⏱️ Your session has expired. Please sign in again.")
            clear_session()
            if st.button("🔑 Sign in", type="primary"):
                st.switch_page("app.py")
            st.stop()
        st.error(f"Could not load report: {exc}")
        report = None

if report is None:
    st.error("Report not found or you don't have access.")
    if st.button("← Back to home"):
        st.switch_page("app.py")
    st.stop()

# ── Check if still evaluating (empty JSON blobs) ──────────────────────────────
if not report.summary_json or not report.detailed_json:
    st.info(
        "⏳ Your report is still being generated. This usually takes 10–30 seconds. "
        "The page will refresh automatically."
    )
    import time

    time.sleep(5)
    st.rerun()

# ── Page header ────────────────────────────────────────────────────────────────
st.title("📈 Interview Report")

tab_summary, tab_detailed, tab_raw = st.tabs(["📋 Summary", "🔍 Detailed", "🧾 Raw JSON"])

with tab_summary:
    try:
        render_summary(report.summary_json)
    except Exception as exc:
        st.error(f"Could not render summary: {exc}")
        st.json(report.summary_json)

with tab_detailed:
    try:
        render_detailed(report.detailed_json)
    except Exception as exc:
        st.error(f"Could not render detailed report: {exc}")
        st.json(report.detailed_json)

with tab_raw:
    # KEY ASSIGNMENT REQUIREMENT: Show both JSON formats clearly labelled
    st.subheader("Format 1: Summary Report")
    st.caption("Compact format for quick overview — schema_version 1.0, format_type 'summary'")
    st.code(json.dumps(report.summary_json, indent=2, default=str), language="json")

    st.divider()

    st.subheader("Format 2: Detailed Report")
    st.caption(
        "Full analysis with per-question breakdown — schema_version 1.0, format_type 'detailed'"
    )
    st.code(json.dumps(report.detailed_json, indent=2, default=str), language="json")

# ── Footer actions ─────────────────────────────────────────────────────────────
st.divider()
col1, col2, col3 = st.columns(3)

with col1:
    export_data = {
        "summary": report.summary_json,
        "detailed": report.detailed_json,
    }
    st.download_button(
        "📥 Export as JSON",
        data=json.dumps(export_data, indent=2, default=str),
        file_name=f"interview_report_{session_id_str[:8]}.json",
        mime="application/json",
    )

with col2:
    if not share_token and get_current_user_id() and st.button("🔗 Generate share link"):
        try:
            from lib.db.sessions import enable_share

            share_url = enable_share(UUID(session_id_str), get_access_token() or "")
            st.success("Share link created!")
            st.code(share_url)
        except Exception as exc:
            st.error(f"Could not generate share link: {exc}")

with col3:
    if st.button("🆕 Start new interview"):
        st.switch_page("app.py")
