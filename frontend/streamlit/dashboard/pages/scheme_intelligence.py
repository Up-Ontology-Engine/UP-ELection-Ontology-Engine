"""
Page 4 — Scheme Intelligence
Shows scheme coverage, sentiment, and execution gaps across the AC.
"""
from __future__ import annotations
import requests
import streamlit as st
import plotly.graph_objects as go
from dashboard.components.war_room import inject_css, section, info_bar, PLOTLY_LAYOUT


GAP_META = {
    "execution_gap":   {"icon": "⚠️", "color": "#e74c3c", "label": "Execution Gap"},
    "reach_gap":       {"icon": "📍", "color": "#e67e22", "label": "Reach Gap"},
    "awareness_gap":   {"icon": "💬", "color": "#f39c12", "label": "Awareness Gap"},
    "performing_well": {"icon": "✅", "color": "#2ecc71", "label": "Performing Well"},
    "in_progress":     {"icon": "🔄", "color": "#3498db", "label": "In Progress"},
    "no_data":         {"icon": "❓", "color": "#95a5a6", "label": "No Data"},
}

SCHEME_ICONS = {
    "jal": "💧", "water": "💧", "pmay": "🏠", "housing": "🏠",
    "mgnrega": "👷", "employment": "💼", "pm-kisan": "🌾", "kisan": "🌾",
    "swachh": "🧹", "ayushman": "🏥", "health": "🏥", "ujjwala": "🔥",
    "saubhagya": "⚡", "electricity": "⚡", "sugarcane": "🎋",
}


def _scheme_icon(name: str) -> str:
    lower = name.lower()
    for key, icon in SCHEME_ICONS.items():
        if key in lower:
            return icon
    return "📋"


@st.cache_data(ttl=120, show_spinner=False)
def _fetch_schemes(ac_id: str, api_url: str) -> list[dict]:
    try:
        r = requests.get(f"{api_url}/ac/{ac_id}/schemes", timeout=10)
        r.raise_for_status()
        return r.json().get("schemes", [])
    except Exception:
        return []


@st.cache_data(ttl=120, show_spinner=False)
def _fetch_booths(ac_id: str, api_url: str) -> list[dict]:
    try:
        r = requests.get(f"{api_url}/ac/{ac_id}/booths", timeout=10)
        r.raise_for_status()
        return r.json().get("booths", [])
    except Exception:
        return []


def render(ac_id: str, ac_name: str, api_url: str) -> None:
    inject_css()

    st.markdown(f"## 🏛️ Scheme Intelligence")
    info_bar(f"AC: {ac_name} ({ac_id})  |  Scheme coverage + execution gap analysis across all booths")

    schemes = _fetch_schemes(ac_id, api_url)
    booths  = _fetch_booths(ac_id, api_url)

    if not schemes:
        st.warning("No scheme data loaded yet.")
        st.code("Run: python -m etl.transform_schemes  +  python -m analytics.scheme_gap")
        _render_demo(ac_name)
        return

    _render_summary_row(schemes, booths)
    st.divider()

    col_left, col_right = st.columns([1.4, 1])
    with col_left:
        _render_scheme_cards(schemes)
    with col_right:
        _render_gap_donut(schemes)
        st.divider()
        _render_priority_matrix(schemes)


def _render_summary_row(schemes: list[dict], _booths: list[dict]) -> None:
    total       = len(schemes)
    gaps        = sum(1 for s in schemes if s.get("gap_type") in ("execution_gap", "reach_gap"))
    performing  = sum(1 for s in schemes if s.get("gap_type") == "performing_well")
    high_pri    = sum(1 for s in schemes if s.get("priority") == "HIGH")
    beneficiries = sum(s.get("beneficiary_count") or 0 for s in schemes)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Schemes Tracked", total)
    c2.metric("With Gaps", gaps, delta=f"{gaps/total*100:.0f}% of total" if total else "")
    c3.metric("Performing Well", performing)
    c4.metric("High Priority", high_pri)
    c5.metric("Total Beneficiaries", f"{beneficiries:,}")


def _render_scheme_cards(schemes: list[dict]) -> None:
    section("Scheme Gap Analysis", "📊")

    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    sorted_schemes = sorted(schemes, key=lambda s: priority_order.get(s.get("priority", "LOW"), 3))

    for s in sorted_schemes[:12]:
        name      = s.get("scheme_name", "Unknown Scheme")
        gap_type  = s.get("gap_type") or "no_data"
        gap_label = s.get("gap_label") or GAP_META.get(gap_type, {}).get("label", "")
        priority  = s.get("priority", "LOW")
        bcount    = s.get("beneficiary_count") or s.get("booth_count", 0) * 250 or 0
        issue_tag = s.get("issue_tag", "")
        avg_sent  = s.get("avg_sentiment") or 0
        pos_ev    = s.get("positive_events") or 0
        neg_ev    = s.get("negative_events") or 0

        meta      = GAP_META.get(gap_type, GAP_META["no_data"])
        color     = meta["color"]
        icon      = meta["icon"]
        s_icon    = _scheme_icon(name)

        pri_color = {"HIGH": "#e74c3c", "MEDIUM": "#f39c12", "LOW": "#2ecc71"}.get(priority, "#95a5a6")
        sent_text = (
            f"😊 {pos_ev} positive" if avg_sent > 0.1 else
            f"😡 {neg_ev} negative" if avg_sent < -0.1 else
            f"😐 mixed signals"
        )

        st.markdown(
            f"""<div style="background:#0f1729;border-left:4px solid {color};
            border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:10px">
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-weight:700;font-size:1.05em">{s_icon} {name}</span>
              <span style="background:{pri_color}22;color:{pri_color};border:1px solid {pri_color};
                border-radius:10px;padding:2px 9px;font-size:.75em;font-weight:700">{priority}</span>
            </div>
            <div style="margin-top:8px;display:flex;gap:16px;flex-wrap:wrap">
              <span style="color:{color};font-weight:700">{icon} {GAP_META.get(gap_type,{}).get('label','')}</span>
              <span style="color:#8b949e;font-size:.88em">{sent_text}</span>
              <span style="color:#8b949e;font-size:.88em">👥 {bcount:,} beneficiaries</span>
              {f'<span style="color:#8b949e;font-size:.88em">🏷️ {issue_tag}</span>' if issue_tag else ''}
            </div>
            {f'<div style="margin-top:6px;color:#8b949e;font-size:.83em">{gap_label[:120]}</div>' if gap_label else ''}
            </div>""",
            unsafe_allow_html=True,
        )


def _render_gap_donut(schemes: list[dict]) -> None:
    section("Gap Distribution", "🍩")
    counts: dict[str, int] = {}
    for s in schemes:
        gt = s.get("gap_type") or "no_data"
        counts[gt] = counts.get(gt, 0) + 1

    labels = [GAP_META.get(k, {}).get("label", k) for k in counts]
    values = list(counts.values())
    colors = [GAP_META.get(k, {}).get("color", "#95a5a6") for k in counts]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        marker=dict(colors=colors, line=dict(color="#0a0e1a", width=2)),
        hole=0.55,
        textinfo="percent+label",
        textfont=dict(size=11),
    ))
    fig.update_layout(**{**PLOTLY_LAYOUT, "height": 280, "showlegend": False,
                         "margin": dict(l=0, r=0, t=10, b=0)})
    st.plotly_chart(fig, use_container_width=True)


def _render_priority_matrix(schemes: list[dict]) -> None:
    section("Priority Matrix", "🎯")
    for priority in ["HIGH", "MEDIUM", "LOW"]:
        batch = [s for s in schemes if s.get("priority") == priority]
        if not batch:
            continue
        color = {"HIGH": "#e74c3c", "MEDIUM": "#f39c12", "LOW": "#2ecc71"}[priority]
        names = ", ".join(s.get("scheme_name", "?")[:20] for s in batch[:3])
        extra = f" +{len(batch)-3} more" if len(batch) > 3 else ""
        st.markdown(
            f"""<div style="background:{color}11;border:1px solid {color}44;
            border-radius:6px;padding:8px 12px;margin-bottom:6px">
            <b style="color:{color}">{priority}</b>
            <span style="color:#8b949e;font-size:.85em">{names}{extra}</span>
            </div>""",
            unsafe_allow_html=True,
        )


def _render_demo(_ac_name: str) -> None:
    """Show a realistic demo when no live data exists."""
    st.divider()
    st.caption("📋 Demo view — populate scheme_gap_analysis table to see live data")

    demo = [
        {"scheme_name": "Jal Jeevan Mission", "gap_type": "reach_gap",       "priority": "HIGH",   "beneficiary_count": 1240, "issue_tag": "water"},
        {"scheme_name": "PMAY (Urban)",        "gap_type": "execution_gap",   "priority": "HIGH",   "beneficiary_count": 890,  "issue_tag": "housing"},
        {"scheme_name": "MGNREGA",             "gap_type": "awareness_gap",   "priority": "MEDIUM", "beneficiary_count": 3100, "issue_tag": "jobs"},
        {"scheme_name": "PM-Kisan",            "gap_type": "performing_well", "priority": "LOW",    "beneficiary_count": 5600, "issue_tag": "farmer"},
        {"scheme_name": "Ayushman Bharat",     "gap_type": "in_progress",     "priority": "MEDIUM", "beneficiary_count": 2200, "issue_tag": "health"},
        {"scheme_name": "Ujjwala 2.0",         "gap_type": "performing_well", "priority": "LOW",    "beneficiary_count": 4100, "issue_tag": "other"},
    ]

    col_l, col_r = st.columns([1.4, 1])
    with col_l:
        _render_scheme_cards(demo)
    with col_r:
        _render_gap_donut(demo)
