import streamlit as st

st.set_page_config(page_title="Admin", page_icon="🔒", layout="wide")

from lib.auth.session import (  # noqa: E402
    get_access_token,
    get_current_user_id,
    is_admin,
    is_authenticated,
)

if not is_authenticated() or not is_admin():
    st.error("Access denied. Admin only.")
    if st.button("← Go to home"):
        st.switch_page("app.py")
    st.stop()

from lib.db.client import get_service_client  # noqa: E402
from lib.db.evaluations import get_scores_by_technique  # noqa: E402
from lib.openrouter.cost_calculator import format_eur  # noqa: E402

st.title("🔒 Admin Dashboard")

service_client = get_service_client()
access_token: str = get_access_token() or ""
user_id = get_current_user_id()

tab_security, tab_prompts, tab_cost, tab_sessions = st.tabs(
    ["🛡️ Security Events", "📊 Prompt Comparison", "💰 Cost Dashboard", "📋 Recent Sessions"]
)

# ── Security Events ────────────────────────────────────────────────────────────
with tab_security:
    st.subheader("Security Events")
    try:
        events_resp = (
            service_client.table("security_events")
            .select("*")
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
        if events_resp.data:
            import pandas as pd

            df = pd.DataFrame(events_resp.data)
            display_cols = [
                c
                for c in [
                    "created_at",
                    "event_type",
                    "severity",
                    "detection_method",
                    "detection_confidence",
                    "blocked",
                    "ip_hash",
                    "input_excerpt",
                ]
                if c in df.columns
            ]
            st.dataframe(df[display_cols], use_container_width=True)
        else:
            st.info("No security events recorded.")
    except Exception as exc:
        st.error(f"Could not load security events: {exc}")

# ── Prompt Comparison ──────────────────────────────────────────────────────────
with tab_prompts:
    st.subheader("Average Score by Prompt Technique")
    try:
        scores = get_scores_by_technique(user_id, access_token) if user_id else {}

        if not scores:
            # Aggregate across all sessions using service client
            agg_resp = (
                service_client.table("sessions")
                .select("prompt_technique")
                .eq("status", "completed")
                .execute()
            )
            # Fallback: show message
            st.info("No completed sessions with scores yet.")
        else:
            techniques = list(scores.keys())
            avg_scores = [scores[t] for t in techniques]
            chart_data = {"Technique": techniques, "Avg Score": avg_scores}
            import pandas as pd

            st.bar_chart(pd.DataFrame(chart_data).set_index("Technique"))
    except Exception as exc:
        st.error(f"Could not load prompt comparison: {exc}")

# ── Cost Dashboard ─────────────────────────────────────────────────────────────
with tab_cost:
    st.subheader("Cost Overview")
    try:
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)

        def _sum_cost(since: datetime) -> int:
            resp = (
                service_client.table("sessions")
                .select("total_cost_usd_cents")
                .gte("created_at", since.isoformat())
                .execute()
            )
            return sum(r.get("total_cost_usd_cents", 0) for r in (resp.data or []))

        cost_today = _sum_cost(today_start)
        cost_week = _sum_cost(week_start)
        cost_month = _sum_cost(month_start)

        c1, c2, c3 = st.columns(3)
        c1.metric("Today", format_eur(cost_today))
        c2.metric("Last 7 days", format_eur(cost_week))
        c3.metric("Last 30 days", format_eur(cost_month))
    except Exception as exc:
        st.error(f"Could not load cost data: {exc}")

# ── Recent Sessions ────────────────────────────────────────────────────────────
with tab_sessions:
    st.subheader("Recent Sessions (all users)")
    try:
        recent_resp = (
            service_client.table("sessions")
            .select("id, user_id, domain, status, total_cost_usd_cents, created_at")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        if recent_resp.data:
            import pandas as pd

            df = pd.DataFrame(recent_resp.data)
            if "total_cost_usd_cents" in df.columns:
                df["cost_eur"] = df["total_cost_usd_cents"].apply(
                    lambda c: format_eur(int(c)) if c else "€0.00"
                )
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No sessions found.")
    except Exception as exc:
        st.error(f"Could not load recent sessions: {exc}")
