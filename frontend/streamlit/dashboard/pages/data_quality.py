"""
Page 8 — Data Quality & Confidence
Coverage, geo accuracy, entity resolution, source bias per booth and AC-wide.
"""
from __future__ import annotations
import requests
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from dashboard.components.war_room import inject_css, section, info_bar, badge, PLOTLY_LAYOUT


QUALITY_COLORS = {
    "HIGH":         "#2ecc71",
    "MEDIUM":       "#f39c12",
    "LOW":          "#e67e22",
    "INSUFFICIENT": "#e74c3c",
    "UNKNOWN":      "#8b949e",
}


@st.cache_data(ttl=180, show_spinner=False)
def _fetch_quality(ac_id: str, api_url: str) -> dict:
    try:
        r = requests.get(f"{api_url}/ac/{ac_id}/quality", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


def render(ac_id: str, ac_name: str, booths: list[dict], api_url: str) -> None:
    inject_css()

    st.markdown("## ⚠️ Data Quality & Confidence")
    info_bar(f"AC: {ac_name}  |  Coverage, source bias, geo accuracy, and entity resolution metrics")

    quality_data = _fetch_quality(ac_id, api_url)

    if not quality_data:
        st.warning("No quality metrics computed yet.")
        st.code("Run: python -m analytics.quality_metrics")
        _render_demo(ac_name, booths)
        return

    summary = quality_data.get("summary", {})
    booth_quality = quality_data.get("booths", [])

    _render_ac_summary(summary, booths)
    st.divider()

    col_l, col_r = st.columns([1.2, 1])
    with col_l:
        _render_source_breakdown(summary)
    with col_r:
        _render_quality_gauge(summary)

    st.divider()
    _render_booth_quality_table(booth_quality)
    st.divider()
    _render_bias_panel(summary)


def _render_ac_summary(summary: dict, booths: list[dict]) -> None:
    total_booths    = len([b for b in booths if not b["booth_id"].endswith("_TOTAL")])
    booths_with_data = summary.get("booths_with_data", 0)
    avg_quality     = summary.get("avg_quality_score", 0)
    total_events    = summary.get("total_events", 0)
    geo_accuracy    = summary.get("avg_geo_confidence", 0)
    entity_match    = summary.get("entity_match_rate", 0)

    ql = summary.get("overall_quality", "UNKNOWN")
    ql_color = QUALITY_COLORS.get(ql, "#8b949e")

    st.markdown(
        f"""<div style="background:{ql_color}22;border:1px solid {ql_color}44;
        border-radius:10px;padding:14px 20px;margin-bottom:16px;display:flex;gap:20px;flex-wrap:wrap">
        <div><span style="font-size:.75em;color:#8b949e;text-transform:uppercase">Overall Quality</span>
          <div style="font-size:1.8em;font-weight:700;color:{ql_color}">{ql}</div></div>
        <div><span style="font-size:.75em;color:#8b949e;text-transform:uppercase">Quality Score</span>
          <div style="font-size:1.8em;font-weight:700">{avg_quality:.2f}</div></div>
        <div><span style="font-size:.75em;color:#8b949e;text-transform:uppercase">Total Events</span>
          <div style="font-size:1.8em;font-weight:700">{total_events:,}</div></div>
        <div><span style="font-size:.75em;color:#8b949e;text-transform:uppercase">Booths Covered</span>
          <div style="font-size:1.8em;font-weight:700">{booths_with_data}/{total_booths}</div></div>
        <div><span style="font-size:.75em;color:#8b949e;text-transform:uppercase">Geo Accuracy</span>
          <div style="font-size:1.8em;font-weight:700">{geo_accuracy:.0%}</div></div>
        <div><span style="font-size:.75em;color:#8b949e;text-transform:uppercase">Entity Match</span>
          <div style="font-size:1.8em;font-weight:700">{entity_match:.0%}</div></div>
        </div>""",
        unsafe_allow_html=True,
    )


def _render_source_breakdown(summary: dict) -> None:
    section("Source Coverage Breakdown", "📡")

    sources = {
        "YouTube": summary.get("avg_youtube_pct", 0),
        "News":    summary.get("avg_news_pct", 0),
        "Survey":  summary.get("avg_survey_pct", 0),
        "Field":   summary.get("avg_field_pct", 0),
    }

    colors = ["#FF6B35", "#3498db", "#2ecc71", "#9b59b6"]
    fig = go.Figure()
    for (src, pct), col in zip(sources.items(), colors):
        fig.add_trace(go.Bar(
            name=src, x=[src], y=[pct],
            marker_color=col,
            text=[f"{pct:.0f}%"], textposition="auto",
        ))
    fig.update_layout(
        **{**PLOTLY_LAYOUT,
           "height": 240,
           "yaxis": dict(range=[0, 105], ticksuffix="%"),
           "showlegend": False,
           "bargap": 0.3,
           "margin": dict(l=0, r=0, t=20, b=20)},
    )
    st.plotly_chart(fig, use_container_width=True)

    # Bias warning
    dominant = max(sources, key=lambda k: sources[k])
    if sources[dominant] > 60:
        st.warning(
            f"⚠️ **Source concentration risk** — {dominant} accounts for "
            f"{sources[dominant]:.0f}% of all data. "
            "Other sources under-represented; conclusions may be biased."
        )


def _render_quality_gauge(summary: dict) -> None:
    section("Quality Score Gauge", "🎯")

    score = summary.get("avg_quality_score", 0) * 100

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "%", "font": {"size": 28, "color": "#e6edf3"}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#8b949e"},
            "bar":  {"color": _score_color(score / 100)},
            "bgcolor": "#0f1729",
            "bordercolor": "#1e2d4a",
            "steps": [
                {"range": [0,  40],  "color": "#e74c3c22"},
                {"range": [40, 70],  "color": "#f39c1222"},
                {"range": [70, 100], "color": "#2ecc7122"},
            ],
            "threshold": {
                "line": {"color": "#FF6B35", "width": 3},
                "thickness": 0.75,
                "value": 70,
            },
        },
    ))
    fig.update_layout(**{**PLOTLY_LAYOUT, "height": 220, "margin": dict(l=20, r=20, t=20, b=10)})
    st.plotly_chart(fig, use_container_width=True)


def _render_booth_quality_table(booth_quality: list[dict]) -> None:
    section("Booth-Level Quality Breakdown", "📊")

    if not booth_quality:
        st.caption("No per-booth quality data available")
        return

    df = pd.DataFrame(booth_quality)
    display_cols = [c for c in [
        "booth_id", "quality_label", "overall_quality_score", "total_events",
        "unique_sources", "youtube_pct", "news_pct", "survey_pct",
        "avg_geo_confidence", "entity_match_rate",
    ] if c in df.columns]

    def color_quality(val):
        color = QUALITY_COLORS.get(str(val), "#8b949e")
        return f"color: {color}; font-weight: bold"

    styled = df[display_cols].style
    if "quality_label" in display_cols:
        styled = styled.applymap(color_quality, subset=["quality_label"])

    st.dataframe(styled, use_container_width=True, height=320)


def _render_bias_panel(summary: dict) -> None:
    section("Bias & Coverage Risks", "🔬")

    risks = []
    yt_pct   = summary.get("avg_youtube_pct", 0)
    geo_acc  = summary.get("avg_geo_confidence", 0)
    ent_match = summary.get("entity_match_rate", 0)
    cov_pct  = summary.get("booth_coverage_pct", 0)

    if yt_pct > 60:
        risks.append(("⚠️", "YouTube Dominance",
                      f"YouTube accounts for {yt_pct:.0f}% of data. "
                      "Digital-native bias may under-represent rural/offline voters.", "high"))
    if geo_acc < 0.6:
        risks.append(("📍", "Low Geo Resolution",
                      f"Only {geo_acc:.0%} of events mapped to a booth. "
                      "Many events remain at AC level — booth insights unreliable.", "high"))
    if ent_match < 0.5:
        risks.append(("🏷️", "Entity Resolution Gap",
                      f"{ent_match:.0%} entity match rate. "
                      "Sentiment may be mis-attributed to wrong candidates/parties.", "medium"))
    if cov_pct < 0.4:
        risks.append(("📊", "Sparse Booth Coverage",
                      f"Only {cov_pct:.0%} of booths have digital data. "
                      "AC-level conclusions extrapolate heavily.", "high"))
    if not risks:
        st.success("✅ No critical data quality risks detected.")
        return

    for icon, title, body, level in risks:
        color = {"high": "#e74c3c", "medium": "#f39c12", "low": "#2ecc71"}.get(level, "#8b949e")
        st.markdown(
            f"""<div style="background:{color}11;border-left:4px solid {color};
            border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:8px">
            <b style="color:{color}">{icon} {title}</b><br>
            <span style="font-size:.88em;color:#8b949e">{body}</span>
            </div>""",
            unsafe_allow_html=True,
        )


def _score_color(score: float) -> str:
    if score >= 0.7:
        return "#2ecc71"
    if score >= 0.4:
        return "#f39c12"
    return "#e74c3c"


def _render_demo(ac_name: str, booths: list[dict]) -> None:
    st.divider()
    st.caption("📋 Demo view — run analytics.quality_metrics to see live data")

    demo_summary = {
        "overall_quality": "MEDIUM",
        "avg_quality_score": 0.61,
        "total_events": 2847,
        "booths_with_data": 42,
        "avg_geo_confidence": 0.73,
        "entity_match_rate": 0.68,
        "avg_youtube_pct": 58,
        "avg_news_pct": 28,
        "avg_survey_pct": 8,
        "avg_field_pct": 6,
        "booth_coverage_pct": 0.45,
    }

    _render_ac_summary(demo_summary, booths or [{"booth_id": f"demo_{i}"} for i in range(95)])
    st.divider()
    col_l, col_r = st.columns([1.2, 1])
    with col_l:
        _render_source_breakdown(demo_summary)
    with col_r:
        _render_quality_gauge(demo_summary)
    st.divider()
    _render_bias_panel(demo_summary)
