"""AC overview — war-room constituency overview page."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.war_room import PALETTE, PLOTLY_LAYOUT, info_bar, inject_css, section


def render(ac_id: str, ac_name: str, booths: list[dict], api_url: str) -> None:
    inject_css()

    st.markdown("## 🏠 Constituency Overview")
    info_bar(f"AC: {ac_name} ({ac_id})  |  War-room overview of all booths and digital lean")

    if not booths:
        st.error("No booth data available. Is the API running and ETL complete?")
        st.code(
            "uvicorn api.main:app --reload  +  python -m flows.graph.flow_load_graph --stage etl"
        )
        return

    df = pd.DataFrame(booths)

    # Fill nulls
    for col in ["bjp_pulse_score", "opp_pulse_score", "digital_lean", "event_count"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    if "digital_lean_label" not in df.columns:
        df["digital_lean_label"] = "No data"

    _render_summary_strip(df)
    st.divider()

    col_left, col_right = st.columns([1.6, 1])
    with col_left:
        _render_lean_distribution(df)
    with col_right:
        _render_historical_lean(df)

    st.divider()
    _render_issue_heatmap(df)
    st.divider()
    _render_booth_table(df)


# ── Sub-components ─────────────────────────────────────────────────────────────


def _render_summary_strip(df: pd.DataFrame) -> None:
    total = len(df[~df["booth_id"].str.endswith("_TOTAL", na=False)])
    with_data = int((df.get("event_count", pd.Series(dtype=float)) > 0).sum())
    bjp_avg = df["bjp_pulse_score"].mean() if "bjp_pulse_score" in df.columns else 0
    opp_avg = df["opp_pulse_score"].mean() if "opp_pulse_score" in df.columns else 0
    lean_bjp = int(
        (df.get("digital_lean_label", pd.Series(dtype=str)).str.contains("BJP", na=False)).sum()
    )
    lean_opp = int(
        (df.get("digital_lean_label", pd.Series(dtype=str)).str.contains("Opp", na=False)).sum()
    )

    overall_lean = (
        "Lean BJP"
        if bjp_avg > opp_avg + 0.05
        else "Lean Opposition"
        if opp_avg > bjp_avg + 0.05
        else "Contested"
    )
    lean_color = {"Lean BJP": "#FF6B35", "Lean Opposition": "#3498db"}.get(overall_lean, "#8b949e")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Booths", total)
    c2.metric("Booths with Data", with_data)
    c3.metric("BJP Pulse (avg)", f"{bjp_avg:+.3f}")
    c4.metric("Opp Pulse (avg)", f"{opp_avg:+.3f}")
    c5.metric("Lean BJP Booths", lean_bjp)
    c6.metric("Lean Opp Booths", lean_opp)

    st.markdown(
        f"""<div style="background:{lean_color}22;border:1px solid {lean_color}44;
        border-radius:8px;padding:10px 18px;margin-top:10px;font-family:monospace">
        <span style="color:{lean_color};font-weight:700;font-size:1.1em">
        ◉ OVERALL CONSTITUENCY LEAN: {overall_lean.upper()}</span>
        </div>""",
        unsafe_allow_html=True,
    )


def _render_lean_distribution(df: pd.DataFrame) -> None:
    section("Booth Lean Distribution", "📊")

    COLOR_MAP = {
        "Lean BJP": PALETTE["bjp"],
        "Slightly BJP": "#FFA07A",
        "Contested": PALETTE["neutral"],
        "Slightly Opp": "#87CEEB",
        "Lean Opposition": PALETTE["sp"],
        "No data": "#2d3a4f",
    }

    lean_counts = (
        df["digital_lean_label"].value_counts().reset_index()
        if "digital_lean_label" in df.columns
        else pd.DataFrame({"digital_lean_label": ["No data"], "count": [len(df)]})
    )
    lean_counts.columns = ["lean", "count"]

    colors = [COLOR_MAP.get(l, "#8b949e") for l in lean_counts["lean"]]
    fig = go.Figure(
        go.Bar(
            x=lean_counts["lean"],
            y=lean_counts["count"],
            marker_color=colors,
            text=lean_counts["count"],
            textposition="auto",
        )
    )
    fig.update_layout(
        **{
            **PLOTLY_LAYOUT,
            "height": 260,
            "yaxis": dict(showgrid=True, gridcolor="#1e2d4a"),
            "showlegend": False,
        },
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_historical_lean(df: pd.DataFrame) -> None:
    section("Pulse Score Distribution", "📈")

    bjp_scores = (
        df["bjp_pulse_score"].dropna()
        if "bjp_pulse_score" in df.columns
        else pd.Series(dtype=float)
    )
    opp_scores = (
        df["opp_pulse_score"].dropna()
        if "opp_pulse_score" in df.columns
        else pd.Series(dtype=float)
    )

    fig = go.Figure()
    if len(bjp_scores) > 0:
        fig.add_trace(
            go.Histogram(
                x=bjp_scores,
                name="BJP",
                marker_color=PALETTE["bjp"],
                opacity=0.75,
                nbinsx=20,
            )
        )
    if len(opp_scores) > 0:
        fig.add_trace(
            go.Histogram(
                x=opp_scores,
                name="Opposition",
                marker_color=PALETTE["sp"],
                opacity=0.75,
                nbinsx=20,
            )
        )
    fig.add_vline(x=0, line_dash="dash", line_color="#8b949e", line_width=1)
    fig.update_layout(
        **{
            **PLOTLY_LAYOUT,
            "height": 260,
            "barmode": "overlay",
            "xaxis": dict(title="Pulse Score"),
            "yaxis": dict(title="Booths", showgrid=True, gridcolor="#1e2d4a"),
        },
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_issue_heatmap(df: pd.DataFrame) -> None:
    section("Top Issue by Booth (sample)", "🔥")

    if "top_issue" not in df.columns:
        st.caption("No issue data available yet")
        return

    issue_counts = df["top_issue"].dropna().value_counts().head(10).reset_index()
    issue_counts.columns = ["issue", "booths"]
    issue_counts["issue"] = issue_counts["issue"].str.replace("_", " ").str.title()

    ISSUE_COLORS = {
        "Water": "#3498db",
        "Jobs": "#e74c3c",
        "Roads": "#95a5a6",
        "Electricity": "#f39c12",
        "Farmer": "#2ecc71",
        "Health": "#e67e22",
        "Education": "#9b59b6",
        "Corruption": "#e74c3c",
        "Price Rise": "#f39c12",
    }

    colors = [ISSUE_COLORS.get(i, "#FF6B35") for i in issue_counts["issue"]]
    fig = go.Figure(
        go.Bar(
            x=issue_counts["booths"],
            y=issue_counts["issue"],
            orientation="h",
            marker_color=colors,
            text=issue_counts["booths"],
            textposition="auto",
        )
    )
    fig.update_layout(
        **{
            **PLOTLY_LAYOUT,
            "height": 280,
            "xaxis": dict(title="Number of booths", showgrid=True, gridcolor="#1e2d4a"),
            "yaxis": dict(autorange="reversed"),
            "margin": dict(l=0, r=40, t=20, b=20),
        },
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_booth_table(df: pd.DataFrame) -> None:
    section("All Booths", "📋")

    # Filter virtual aggregate booths
    display_df = df[~df["booth_id"].str.endswith("_TOTAL", na=False)].copy()

    display_cols = [
        c
        for c in [
            "booth_number",
            "name",
            "total_voters",
            "digital_lean_label",
            "bjp_pulse_score",
            "opp_pulse_score",
            "top_issue",
            "confidence_label",
            "event_count",
        ]
        if c in display_df.columns
    ]

    rename = {
        "booth_number": "#",
        "name": "Polling Station",
        "total_voters": "Voters",
        "digital_lean_label": "Digital Lean",
        "bjp_pulse_score": "BJP",
        "opp_pulse_score": "Opp",
        "top_issue": "Top Issue",
        "confidence_label": "Confidence",
        "event_count": "Events",
    }

    st.dataframe(
        display_df[display_cols].rename(columns=rename),
        use_container_width=True,
        height=480,
    )
