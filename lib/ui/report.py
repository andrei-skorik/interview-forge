from __future__ import annotations

from typing import Any

import streamlit as st

from lib.schemas.judge import DetailedReport, SummaryReport


def render_summary(report_data: dict[str, Any] | SummaryReport) -> None:
    """Render the summary report section."""
    summary: SummaryReport
    if isinstance(report_data, dict):
        summary = SummaryReport.model_validate(report_data)
    else:
        summary = report_data

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Overall Score", f"{summary.overall_score:.1f}/10")
    with col2:
        st.metric("Readiness", summary.readiness_level.replace("_", " ").title())
    with col3:
        st.metric("Domain", summary.domain.replace("_", " ").title())

    st.markdown(f"### Verdict\n{summary.verdict}")

    col_s, col_w = st.columns(2)
    with col_s:
        st.markdown("#### Strengths")
        for strength in summary.top_strengths:
            st.markdown(f"✅ {strength}")
    with col_w:
        st.markdown("#### Areas to improve")
        for weakness in summary.top_weaknesses:
            st.markdown(f"⚠️ {weakness}")

    st.markdown("#### Next Actions")
    priority_icons: dict[str, str] = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    for action in summary.next_actions:
        icon = priority_icons.get(action.priority, "⚪")
        st.markdown(f"{icon} **{action.priority.title()}** — {action.action}")


def render_detailed(report_data: dict[str, Any] | DetailedReport) -> None:
    """Render the detailed report section with radar chart and per-question breakdown."""
    detailed: DetailedReport
    if isinstance(report_data, dict):
        detailed = DetailedReport.model_validate(report_data)
    else:
        detailed = report_data

    # Radar chart
    try:
        import plotly.graph_objects as go

        criteria = ["Correctness", "Depth", "Structure", "Communication"]
        scores_map = detailed.overall_assessment.scores_by_criterion
        scores = [scores_map.get(c.lower(), scores_map.get(c, None)) for c in criteria]
        score_values = [s.average if s is not None else 0.0 for s in scores]

        fig = go.Figure(
            data=go.Scatterpolar(
                r=score_values + [score_values[0]],
                theta=criteria + [criteria[0]],
                fill="toself",
                line={"color": "#10b981"},
                fillcolor="rgba(16, 185, 129, 0.2)",
                name="Scores",
            )
        )
        fig.update_layout(
            polar={"radialaxis": {"visible": True, "range": [0, 10]}},
            showlegend=False,
            margin={"l": 40, "r": 40, "t": 40, "b": 40},
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.warning("Could not render radar chart.")

    oa = detailed.overall_assessment
    st.markdown(f"**Overall: {oa.overall_score:.1f}/10** — {oa.verdict}")

    st.divider()
    st.markdown("### Question-by-Question Breakdown")

    for i, q_eval in enumerate(detailed.question_by_question, 1):
        question_preview = q_eval.question[:60] + ("..." if len(q_eval.question) > 60 else "")
        with st.expander(f"Q{i}: {question_preview}"):
            st.markdown(f"**Score: {q_eval.scores.average:.1f}/10**")
            col_q, col_a = st.columns([1, 2])
            with col_q:
                st.markdown("**Question:**")
                st.markdown(q_eval.question)
            with col_a:
                st.markdown("**Your answer:**")
                st.markdown(q_eval.user_answer)

            st.markdown("**Feedback:**")
            st.markdown(
                f"- Correctness ({q_eval.scores.correctness}/10): {q_eval.reasoning.correctness}"
            )
            st.markdown(f"- Depth ({q_eval.scores.depth}/10): {q_eval.reasoning.depth}")
            st.markdown(f"- Structure ({q_eval.scores.structure}/10): {q_eval.reasoning.structure}")
            st.markdown(
                f"- Communication ({q_eval.scores.communication}/10): "
                f"{q_eval.reasoning.communication}"
            )

    st.divider()
    st.markdown("#### Improvement Plan")
    priority_icons: dict[str, str] = {"high": "🔴", "medium": "🟡", "low": "🟢"}

    for item in detailed.improvement_plan:
        icon = priority_icons.get(item.priority, "⚪")
        with st.expander(f"{icon} {item.action} (~{item.estimated_hours}h)"):
            st.markdown(f"**Success criterion:** {item.success_criterion}")
            if item.resources:
                st.markdown("**Resources:**")
                for r in item.resources:
                    if r.url:
                        st.markdown(f"- [{r.title}]({r.url}) ({r.type})")
                    else:
                        st.markdown(f"- {r.title} ({r.type})")
