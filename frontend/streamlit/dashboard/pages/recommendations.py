"""
Page 9 — Recommendations & Risk Engine
Strategic risks, opportunities, and action checklist derived from all data layers.
"""

from __future__ import annotations

import plotly.graph_objects as go
import requests
import streamlit as st

from dashboard.components.war_room import PLOTLY_LAYOUT, info_bar, inject_css, risk_row, section


@st.cache_data(ttl=120, show_spinner=False)
def _fetch_recommendations(ac_id: str, api_url: str) -> dict:
    try:
        r = requests.get(f"{api_url}/ac/{ac_id}/recommendations", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_booths(ac_id: str, api_url: str) -> list[dict]:
    try:
        r = requests.get(f"{api_url}/ac/{ac_id}/booths", timeout=10)
        r.raise_for_status()
        return r.json().get("booths", [])
    except Exception:
        return []


def render(ac_id: str, ac_name: str, booths: list[dict], api_url: str) -> None:
    inject_css()

    st.markdown("## 🚨 Recommendations & Risk Engine")
    info_bar(
        f"AC: {ac_name}  |  AI-synthesised strategic risks, opportunities, and action priorities"
    )

    recs = _fetch_recommendations(ac_id, api_url)
    if not recs:
        recs = _synthesise_from_booths(booths)

    if not recs:
        st.info(
            "Not enough data for recommendations yet. Run the full ETL + analytics pipeline first."
        )
        _render_demo(ac_name)
        return

    _render_overall_signal(recs)
    st.divider()

    col_l, col_r = st.columns(2)
    with col_l:
        _render_risks(recs.get("risks", []))
    with col_r:
        _render_opportunities(recs.get("opportunities", []))

    st.divider()
    _render_action_plan(recs.get("actions", []))
    st.divider()
    _render_priority_matrix_chart(recs.get("risks", []), recs.get("opportunities", []))


def _render_overall_signal(recs: dict) -> None:
    lean = recs.get("overall_lean", "Contested")
    conf = recs.get("confidence", "LOW")
    top_risk = recs.get("top_risk", "Unknown")
    top_opp = recs.get("top_opportunity", "Unknown")
    verdict = recs.get("verdict", "Insufficient data for verdict")

    lean_color = "#FF6B35" if "BJP" in lean else "#3498db" if "Opp" in lean else "#8b949e"
    conf_color = {"HIGH": "#2ecc71", "MEDIUM": "#f39c12", "LOW": "#e74c3c"}.get(conf, "#8b949e")

    cols = st.columns([2, 1, 1, 1])
    with cols[0]:
        st.markdown(
            f"""<div style="background:{lean_color}22;border:1px solid {lean_color}44;
            border-radius:10px;padding:14px 18px">
            <div style="font-size:.75em;color:#8b949e;text-transform:uppercase">Electoral Lean</div>
            <div style="font-size:1.8em;font-weight:700;color:{lean_color}">{lean}</div>
            <div style="font-size:.88em;color:#8b949e;margin-top:6px">{verdict}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown(
            f"""<div style="background:{conf_color}22;border:1px solid {conf_color}44;
            border-radius:10px;padding:14px 18px;text-align:center">
            <div style="font-size:.75em;color:#8b949e;text-transform:uppercase">Confidence</div>
            <div style="font-size:1.5em;font-weight:700;color:{conf_color}">{conf}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with cols[2]:
        st.markdown(
            f"""<div style="background:#e74c3c22;border:1px solid #e74c3c44;
            border-radius:10px;padding:14px 18px">
            <div style="font-size:.75em;color:#8b949e;text-transform:uppercase">Top Risk</div>
            <div style="font-weight:700;color:#e74c3c;font-size:.95em">{top_risk}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with cols[3]:
        st.markdown(
            f"""<div style="background:#2ecc7122;border:1px solid #2ecc7144;
            border-radius:10px;padding:14px 18px">
            <div style="font-size:.75em;color:#8b949e;text-transform:uppercase">Top Opportunity</div>
            <div style="font-weight:700;color:#2ecc71;font-size:.95em">{top_opp}</div>
            </div>""",
            unsafe_allow_html=True,
        )


def _render_risks(risks: list[dict]) -> None:
    section("Risk Factors", "⚠️")

    if not risks:
        st.caption("No risk data available")
        return

    for r in risks:
        title = r.get("title", "")
        body = r.get("description", "")
        level = r.get("level", "medium")
        icon_map = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        icon = icon_map.get(level, "⚪")
        risk_row(icon, title, body, level)


def _render_opportunities(opportunities: list[dict]) -> None:
    section("Opportunities", "🎯")

    if not opportunities:
        st.caption("No opportunity data available")
        return

    for o in opportunities:
        title = o.get("title", "")
        body = o.get("description", "")
        color = "#2ecc71"
        st.markdown(
            f"""<div style="background:{color}11;border-left:4px solid {color};
            border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:8px">
            <b style="color:{color}">✅ {title}</b><br>
            <span style="font-size:.87em;color:#8b949e">{body}</span>
            </div>""",
            unsafe_allow_html=True,
        )


def _render_action_plan(actions: list[dict]) -> None:
    section("Strategic Action Plan", "📌")

    if not actions:
        st.caption("No specific actions derived yet")
        return

    for i, a in enumerate(actions, 1):
        priority = a.get("priority", "medium")
        title = a.get("title", "")
        body = a.get("description", "")
        deadline = a.get("deadline", "")
        target = a.get("target_segment", "")

        pri_color = {"high": "#e74c3c", "medium": "#f39c12", "low": "#2ecc71"}.get(
            priority, "#8b949e"
        )
        meta_parts = [
            p
            for p in [
                f"🎯 {target}" if target else "",
                f"⏰ {deadline}" if deadline else "",
            ]
            if p
        ]

        st.markdown(
            f"""<div style="background:#0f1729;border:1px solid #1e2d4a;
            border-radius:8px;padding:12px 16px;margin-bottom:8px">
            <div style="display:flex;align-items:center;gap:10px">
              <span style="background:{pri_color};color:#fff;border-radius:50%;width:24px;height:24px;
                display:inline-flex;align-items:center;justify-content:center;font-weight:700;
                font-size:.85em;flex-shrink:0">{i}</span>
              <b>{title}</b>
              <span style="margin-left:auto;background:{pri_color}22;color:{pri_color};
                border-radius:10px;padding:2px 8px;font-size:.75em;font-weight:700">
                {priority.upper()}</span>
            </div>
            <div style="margin-top:6px;color:#8b949e;font-size:.88em">{body}</div>
            {f'<div style="margin-top:4px;font-size:.78em;color:#6b7787">{" · ".join(meta_parts)}</div>' if meta_parts else ''}
            </div>""",
            unsafe_allow_html=True,
        )


def _render_priority_matrix_chart(risks: list[dict], opportunities: list[dict]) -> None:
    section("Priority Matrix (Impact × Urgency)", "📊")

    items = []
    for r in risks:
        items.append(
            {
                "name": r.get("title", "Risk"),
                "impact": {"high": 9, "medium": 5, "low": 2}.get(r.get("level", "medium"), 5),
                "urgency": r.get("urgency_score", 5),
                "type": "Risk",
                "color": "#e74c3c",
            }
        )
    for o in opportunities:
        items.append(
            {
                "name": o.get("title", "Opp"),
                "impact": o.get("impact_score", 5),
                "urgency": o.get("urgency_score", 4),
                "type": "Opportunity",
                "color": "#2ecc71",
            }
        )

    if not items:
        st.caption("Matrix requires risk/opportunity data")
        return

    fig = go.Figure()
    for t, col in [("Risk", "#e74c3c"), ("Opportunity", "#2ecc71")]:
        subset = [x for x in items if x["type"] == t]
        if subset:
            fig.add_trace(
                go.Scatter(
                    x=[x["urgency"] for x in subset],
                    y=[x["impact"] for x in subset],
                    mode="markers+text",
                    name=t,
                    text=[x["name"][:20] for x in subset],
                    textposition="top center",
                    textfont=dict(size=9),
                    marker=dict(
                        size=18, color=col, opacity=0.85, line=dict(color="#0a0e1a", width=2)
                    ),
                )
            )

    fig.add_vrect(x0=6.5, x1=10, fillcolor="#e74c3c", opacity=0.04, line_width=0)
    fig.add_hrect(y0=6.5, y1=10, fillcolor="#e74c3c", opacity=0.04, line_width=0)
    fig.update_layout(
        **{
            **PLOTLY_LAYOUT,
            "height": 320,
            "xaxis": dict(range=[0, 10.5], title="Urgency", showgrid=True, gridcolor="#1e2d4a"),
            "yaxis": dict(range=[0, 10.5], title="Impact", showgrid=True, gridcolor="#1e2d4a"),
            "margin": dict(l=40, r=0, t=20, b=40),
        },
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Top-right quadrant = High impact + High urgency → act immediately")


def _synthesise_from_booths(booths: list[dict]) -> dict:
    """Generate basic recommendations from booth metric data if API endpoint missing."""
    if not booths:
        return {}

    data_booths = [b for b in booths if (b.get("event_count") or 0) > 0]
    bjp_avg = sum(b.get("bjp_pulse_score") or 0 for b in data_booths) / max(len(data_booths), 1)
    opp_avg = sum(b.get("opp_pulse_score") or 0 for b in data_booths) / max(len(data_booths), 1)

    lean = (
        "Lean BJP"
        if bjp_avg > opp_avg + 0.1
        else "Lean Opposition"
        if opp_avg > bjp_avg + 0.1
        else "Contested"
    )

    top_issues: dict[str, int] = {}
    for b in booths:
        ti = b.get("top_issue")
        if ti:
            top_issues[ti] = top_issues.get(ti, 0) + 1

    top_issue_list = sorted(top_issues, key=lambda k: top_issues[k], reverse=True)[:3]

    risks = [
        {
            "title": f"{issue.replace('_',' ').title()} Dissatisfaction",
            "description": f"{top_issues[issue]} booths flagging {issue} as top concern",
            "level": "high" if top_issues[issue] > 10 else "medium",
            "urgency_score": 7,
        }
        for issue in top_issue_list
    ]

    return {
        "overall_lean": lean,
        "confidence": "MEDIUM" if len(data_booths) > 20 else "LOW",
        "top_risk": risks[0]["title"] if risks else "Insufficient data",
        "top_opportunity": "Incumbent base — consolidate rural voters",
        "verdict": f"Based on {len(data_booths)} booths with digital data",
        "risks": risks,
        "opportunities": [
            {
                "title": "Incumbent Base Retention",
                "description": "Historical BJP stronghold — consolidate base with targeted outreach",
                "impact_score": 8,
                "urgency_score": 6,
            },
            {
                "title": "Women Voter Mobilisation",
                "description": "Female voter ratio relatively stable — targeted welfare messaging",
                "impact_score": 7,
                "urgency_score": 5,
            },
        ],
        "actions": [
            {
                "title": f"Address {ti.replace('_',' ').title()} delivery gap",
                "description": f"Prioritise booths with high {ti} dissatisfaction for outreach",
                "priority": "high",
                "target_segment": "Affected households",
                "deadline": "ASAP",
            }
            for ti in top_issue_list[:2]
        ]
        + [
            {
                "title": "Deploy field surveyors to data-sparse booths",
                "description": "Low data confidence in some booths. Ground-truth digital signals.",
                "priority": "medium",
                "target_segment": "Survey team",
                "deadline": "2 weeks",
            },
        ],
    }


def _render_demo(ac_name: str) -> None:
    st.divider()
    st.caption("📋 Demo view — complete the ETL and analytics pipeline to see live recommendations")

    demo = {
        "overall_lean": "Lean BJP",
        "confidence": "MEDIUM",
        "top_risk": "Water & Employment Dissatisfaction",
        "top_opportunity": "Strong historical base + women voters stable",
        "verdict": "BJP holds edge but facing anti-incumbency headwinds",
        "risks": [
            {
                "title": "Water Supply Dissatisfaction",
                "level": "high",
                "urgency_score": 8,
                "description": "23 booths flag water as top issue; negative sentiment rising 22% in 30 days",
            },
            {
                "title": "Youth Employment Frustration",
                "level": "high",
                "urgency_score": 8,
                "description": "Paper leak + job scarcity driving 18-25 age group toward opposition",
            },
            {
                "title": "Anti-Incumbency Narrative",
                "level": "medium",
                "urgency_score": 6,
                "description": "Development narrative declining; employment crisis narrative rising",
            },
            {
                "title": "BJP Vote Share Decline",
                "level": "medium",
                "urgency_score": 5,
                "description": "BJP share dropped from 52% (2017) to 48% (2022) — trend needs reversal",
            },
        ],
        "opportunities": [
            {
                "title": "Strong Historical Base",
                "impact_score": 9,
                "urgency_score": 4,
                "description": "BJP won 7 of 9 Gorakhpur ACs in 2022 — base is consolidatable",
            },
            {
                "title": "Women Sentiment Stable",
                "impact_score": 7,
                "urgency_score": 5,
                "description": "Female voter dissatisfaction lower than male — welfare schemes resonating",
            },
            {
                "title": "AIIMS + Infrastructure Positive",
                "impact_score": 6,
                "urgency_score": 3,
                "description": "Government development announcements creating positive signals in 12 booths",
            },
        ],
        "actions": [
            {
                "title": "Water-focused campaign in 23 high-dissatisfaction booths",
                "description": "Deploy Jal Jeevan Mission officials for direct-to-voter outreach in flagged booths",
                "priority": "high",
                "target_segment": "Women + elderly",
                "deadline": "2 weeks",
            },
            {
                "title": "Youth employment outreach — paper leak response",
                "description": "Direct engagement events addressing recruitment transparency concerns",
                "priority": "high",
                "target_segment": "18-30 voters",
                "deadline": "10 days",
            },
            {
                "title": "Address paper leak narrative with facts",
                "description": "Official communication on exam reforms to counter SP narrative",
                "priority": "medium",
                "target_segment": "Students",
                "deadline": "1 month",
            },
            {
                "title": "Expand data collection to 50+ data-sparse booths",
                "description": "Survey team deployment to improve confidence from MEDIUM to HIGH",
                "priority": "medium",
                "target_segment": "Survey team",
                "deadline": "3 weeks",
            },
        ],
    }

    _render_overall_signal(demo)
    st.divider()
    col_l, col_r = st.columns(2)
    with col_l:
        _render_risks(demo["risks"])
    with col_r:
        _render_opportunities(demo["opportunities"])
    st.divider()
    _render_action_plan(demo["actions"])
    st.divider()
    _render_priority_matrix_chart(demo["risks"], demo["opportunities"])
