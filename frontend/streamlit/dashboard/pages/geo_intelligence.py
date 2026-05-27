"""
Page: Geospatial Intelligence
Plotly mapbox scatter showing booth-level political signals.
Color = BJP/opposition lean; size = total voters.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

from dashboard.components.war_room import PLOTLY_LAYOUT, info_bar, inject_css, section

ISSUE_COLORS = {
    "water": "#3498db",
    "roads": "#7f8c8d",
    "electricity": "#f39c12",
    "jobs": "#27ae60",
    "health": "#e74c3c",
    "education": "#9b59b6",
    "corruption": "#c0392b",
    "law_order": "#2c3e50",
    "farmer": "#16a085",
    "women_safety": "#e91e63",
    "price_rise": "#ff5722",
    "sugarcane": "#8bc34a",
    "other": "#95a5a6",
}


@st.cache_data(ttl=180, show_spinner=False)
def _load_geo_data(ac_id: str, api_url: str) -> pd.DataFrame:
    try:
        r = requests.get(f"{api_url}/ac/{ac_id}/geo", timeout=15)
        r.raise_for_status()
        rows = r.json().get("geo", [])
    except Exception:
        rows = []

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df[df["lat"].notna() & df["lon"].notna()].copy()
    df["bjp_pulse"] = pd.to_numeric(df.get("bjp_pulse_score", 0.5), errors="coerce").fillna(0.5)
    df["opp_pulse"] = pd.to_numeric(df.get("opp_pulse_score", 0.5), errors="coerce").fillna(0.5)
    df["digital_lean"] = pd.to_numeric(df.get("digital_lean", 0.0), errors="coerce").fillna(0.0)
    df["total_voters"] = pd.to_numeric(df.get("total_voters", 500), errors="coerce").fillna(500)
    df["top_issue"] = df.get("top_issue", "other").fillna("other")
    df["lean_label"] = df.get("digital_lean_label", "Unknown").fillna("Unknown")
    df["name"] = df.get("name", df.get("booth_id", "")).fillna("")
    return df


def render(ac_id: str, ac_name: str, api_url: str) -> None:
    inject_css()
    st.markdown("## 🗺️ Geospatial Intelligence")
    info_bar(
        f"AC: {ac_name}  |  Booth-level spatial signals — bubble size = voters, colour = political lean"
    )

    col_mode, col_refresh = st.columns([3, 1])
    with col_mode:
        map_mode = st.selectbox(
            "Colour by",
            ["Digital Lean", "BJP Pulse", "Opposition Pulse", "Top Issue"],
            key="geo_mode",
        )
    with col_refresh:
        st.markdown("")
        if st.button("Refresh", use_container_width=True):
            st.cache_data.clear()

    df = _load_geo_data(ac_id, api_url)

    if df.empty:
        st.warning("No geocoded booth data yet.")
        col_a, col_b = st.columns(2)
        with col_a:
            st.info(
                "Step 1: Apply migration 006\n```\npsql $POSTGRES_URL -f db/migrations/006_intelligence_tables.sql\n```"
            )
        with col_b:
            st.info("Step 2: Run geocoder\n```\npython -m etl.geocode_booths\n```")
        _render_placeholder(ac_id)
        return

    # Summary metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Booths mapped", len(df))
    bjp_n = int((df["digital_lean"] > 0.2).sum())
    opp_n = int((df["digital_lean"] < -0.2).sum())
    m2.metric("BJP-leaning booths", bjp_n)
    m3.metric("Opp-leaning booths", opp_n)
    m4.metric("Avg voters/booth", f"{int(df['total_voters'].mean()):,}")

    # Marker size: scaled to voters
    max_v = df["total_voters"].max() or 1
    df["_sz"] = (8 + (df["total_voters"] / max_v) * 18).clip(8, 26)

    center_lat = float(df["lat"].mean())
    center_lon = float(df["lon"].mean())

    fig = go.Figure()

    if map_mode == "Top Issue":
        for issue, grp in df.groupby("top_issue"):
            fig.add_trace(
                go.Scattermapbox(
                    lat=grp["lat"],
                    lon=grp["lon"],
                    mode="markers",
                    name=str(issue).replace("_", " ").title(),
                    marker=dict(size=grp["_sz"], color=ISSUE_COLORS.get(str(issue), "#888")),
                    text=grp.apply(
                        lambda r: (
                            f"<b>{r['name'] or r['booth_id']}</b><br>"
                            f"Issue: {str(r['top_issue']).replace('_',' ').title()}<br>"
                            f"Voters: {int(r['total_voters']):,}"
                        ),
                        axis=1,
                    ),
                    hoverinfo="text",
                )
            )
    else:
        if map_mode == "BJP Pulse":
            color_col, colorscale, ctitle = "bjp_pulse", "Oranges", "BJP Pulse"
        elif map_mode == "Opposition Pulse":
            color_col, colorscale, ctitle = "opp_pulse", "Reds", "Opp Pulse"
        else:
            color_col, colorscale, ctitle = (
                "digital_lean",
                [[0.0, "#FF0000"], [0.5, "#666666"], [1.0, "#FF9933"]],
                "← Opp | BJP →",
            )

        hover = df.apply(
            lambda r: (
                f"<b>{r['name'] or r['booth_id']}</b><br>"
                f"Lean: {r['lean_label']}<br>"
                f"Issue: {str(r['top_issue']).replace('_',' ').title()}<br>"
                f"Voters: {int(r['total_voters']):,}"
            ),
            axis=1,
        )
        fig.add_trace(
            go.Scattermapbox(
                lat=df["lat"],
                lon=df["lon"],
                mode="markers",
                marker=dict(
                    size=df["_sz"],
                    color=df[color_col],
                    colorscale=colorscale,
                    colorbar=dict(title=ctitle, thickness=12, x=1.0, len=0.7),
                    showscale=True,
                    cmin=-1 if color_col == "digital_lean" else 0,
                    cmax=1,
                ),
                text=hover,
                hoverinfo="text",
                name="Booths",
            )
        )

    fig.update_layout(
        mapbox=dict(
            style="carto-darkmatter",
            center=dict(lat=center_lat, lon=center_lon),
            zoom=12,
        ),
        height=520,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#0a0e1a",
        legend=dict(
            orientation="v",
            x=0,
            y=1,
            bgcolor="rgba(10,14,26,0.85)",
            font=dict(color="#e6edf3", size=10),
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Issue distribution bar
    section("Issue Distribution Across Booths", "📊")
    ic = df["top_issue"].value_counts().reset_index()
    ic.columns = ["Issue", "Booths"]
    ic["Issue"] = ic["Issue"].str.replace("_", " ").str.title()
    fig2 = px.bar(
        ic,
        x="Issue",
        y="Booths",
        text="Booths",
        color="Issue",
        color_discrete_sequence=list(ISSUE_COLORS.values()),
    )
    fig2.update_layout(**{**PLOTLY_LAYOUT, "height": 260, "showlegend": False})
    fig2.update_traces(textposition="outside")
    st.plotly_chart(fig2, use_container_width=True)

    # Data table
    section("Booth Data", "📋")
    disp = df[["booth_id", "name", "total_voters", "lean_label", "top_issue", "lat", "lon"]].copy()
    disp.columns = ["Booth ID", "Name", "Voters", "Lean", "Top Issue", "Lat", "Lon"]
    st.dataframe(disp, use_container_width=True, height=300)


def _render_placeholder(ac_id: str) -> None:
    """Centred map placeholder when no geo data exists."""
    fig = go.Figure(
        go.Scattermapbox(
            lat=[26.760],
            lon=[83.375],
            mode="markers+text",
            marker=dict(size=20, color="#FF6B35"),
            text=["Gorakhpur Urban AC"],
            textposition="top right",
        )
    )
    fig.update_layout(
        mapbox=dict(style="carto-darkmatter", center=dict(lat=26.760, lon=83.375), zoom=12),
        height=400,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#0a0e1a",
    )
    st.plotly_chart(fig, use_container_width=True)
