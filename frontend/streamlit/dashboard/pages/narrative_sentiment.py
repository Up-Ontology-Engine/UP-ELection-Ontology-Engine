"""
Page 5 — Narrative & Sentiment Explorer
Rising/declining narrative patterns, emotion breakdown, trigger events.
"""

from __future__ import annotations

import plotly.graph_objects as go
import requests
import streamlit as st

from dashboard.components.war_room import PLOTLY_LAYOUT, info_bar, inject_css, section

NARRATIVE_META = {
    "development_positive": {"icon": "🏗️", "color": "#2ecc71", "label": "Development Positive"},
    "anti_incumbency": {"icon": "📣", "color": "#e74c3c", "label": "Anti-Incumbency"},
    "corruption_narrative": {"icon": "🔍", "color": "#e67e22", "label": "Corruption"},
    "price_rise_narrative": {"icon": "💸", "color": "#f39c12", "label": "Price Rise"},
    "women_safety_narrative": {"icon": "🛡️", "color": "#9b59b6", "label": "Women Safety"},
    "employment_crisis": {"icon": "💼", "color": "#e74c3c", "label": "Employment Crisis"},
    "scheme_success": {"icon": "✅", "color": "#2ecc71", "label": "Scheme Success"},
    "swing_possible": {"icon": "⚖️", "color": "#9b59b6", "label": "Swing Possible"},
    "youth_frustration": {"icon": "🔥", "color": "#e74c3c", "label": "Youth Frustration"},
    "farmer_distress": {"icon": "🌾", "color": "#f39c12", "label": "Farmer Distress"},
}

EMOTION_COLORS = {
    "anger": "#e74c3c",
    "frustration": "#e67e22",
    "hope": "#2ecc71",
    "support": "#3498db",
    "neutral": "#95a5a6",
    "fear": "#9b59b6",
}


@st.cache_data(ttl=120, show_spinner=False)
def _fetch_narratives(ac_id: str, api_url: str) -> list[dict]:
    try:
        r = requests.get(f"{api_url}/ac/{ac_id}/narratives", timeout=10)
        r.raise_for_status()
        return r.json().get("narratives", [])
    except Exception:
        return []


@st.cache_data(ttl=120, show_spinner=False)
def _fetch_booths_narrative(ac_id: str, api_url: str) -> list[dict]:
    try:
        r = requests.get(f"{api_url}/ac/{ac_id}/booths", timeout=10)
        r.raise_for_status()
        booths = r.json().get("booths", [])
        # Fetch narratives for each booth (first 5 with data)
        results = []
        for b in [x for x in booths if x.get("event_count", 0) > 0][:5]:
            try:
                nr = requests.get(f"{api_url}/booth/{b['booth_id']}/narratives", timeout=5)
                if nr.ok:
                    for n in nr.json().get("narratives", []):
                        n["booth_id"] = b["booth_id"]
                        n["booth_number"] = b.get("booth_number", "?")
                        results.append(n)
            except Exception:
                pass
        return results
    except Exception:
        return []


def render(ac_id: str, ac_name: str, window_days: int, api_url: str) -> None:
    inject_css()

    st.markdown("## 🌊 Narrative & Sentiment Explorer")
    info_bar(f"AC: {ac_name}  |  Detecting narrative patterns, emotion trends, and trigger signals")

    narratives = _fetch_narratives(ac_id, api_url)

    if not narratives:
        # Fall back to booth-level aggregation
        narratives = _fetch_booths_narrative(ac_id, api_url)

    if not narratives:
        st.warning("No narrative data yet. Run: `python -m analytics.narrative_engine`")
        _render_demo()
        return

    # Aggregate narrative types
    agg: dict[str, dict] = {}
    for n in narratives:
        nt = n.get("narrative_type", "unknown")
        if nt not in agg:
            agg[nt] = {"strength_sum": 0, "count": 0, "evidence": 0}
        agg[nt]["strength_sum"] += n.get("strength", 0)
        agg[nt]["count"] += 1
        agg[nt]["evidence"] += n.get("evidence_count", 0)

    ranked = sorted(
        [
            {
                "type": k,
                "avg_strength": v["strength_sum"] / v["count"],
                "booth_count": v["count"],
                "evidence": v["evidence"],
            }
            for k, v in agg.items()
        ],
        key=lambda x: x["avg_strength"],
        reverse=True,
    )

    _render_top_row(ranked)
    st.divider()

    col_l, col_r = st.columns([1.3, 1])
    with col_l:
        _render_narrative_bars(ranked)
    with col_r:
        _render_emotion_breakdown(narratives)

    st.divider()
    _render_narrative_detail(narratives)


def _render_top_row(ranked: list[dict]) -> None:
    rising = [r for r in ranked if r["avg_strength"] >= 0.6][:3]
    declining = [r for r in ranked if r["avg_strength"] < 0.3][:2]

    c1, c2, c3 = st.columns(3)
    with c1:
        section("Rising Narratives", "📈")
        if rising:
            for r in rising:
                meta = NARRATIVE_META.get(
                    r["type"], {"icon": "🔹", "color": "#8b949e", "label": r["type"]}
                )
                st.markdown(
                    f"""<div style="background:{meta['color']}22;border-left:3px solid {meta['color']};
                    border-radius:0 6px 6px 0;padding:8px 12px;margin-bottom:6px">
                    <b>{meta['icon']} {meta['label']}</b>
                    <span style="float:right;color:{meta['color']};font-weight:700">
                      {r['avg_strength']:.0%}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No strong rising narratives")

    with c2:
        section("Declining Narratives", "📉")
        if declining:
            for r in declining:
                meta = NARRATIVE_META.get(
                    r["type"], {"icon": "🔹", "color": "#95a5a6", "label": r["type"]}
                )
                st.markdown(
                    f"""<div style="background:#1e2d4a;border-left:3px solid #95a5a6;
                    border-radius:0 6px 6px 0;padding:8px 12px;margin-bottom:6px;opacity:0.7">
                    <b>{meta['icon']} {meta['label']}</b>
                    <span style="float:right;color:#95a5a6">{r['avg_strength']:.0%}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No clearly declining narratives")

    with c3:
        section("Signal Summary", "🎯")
        total_booths = sum(r["booth_count"] for r in ranked)
        total_evidence = sum(r["evidence"] for r in ranked)
        dominant = ranked[0] if ranked else None
        if dominant:
            meta = NARRATIVE_META.get(dominant["type"], {"icon": "🔹", "color": "#FF6B35"})
            st.markdown(
                f"""<div style="background:{meta['color']}22;border:1px solid {meta['color']}44;
                border-radius:8px;padding:12px;text-align:center">
                <div style="font-size:.75em;color:#8b949e;text-transform:uppercase">Dominant Narrative</div>
                <div style="font-size:1.5em">{meta['icon']}</div>
                <div style="font-weight:700;color:{meta['color']}">{meta.get('label', dominant['type'])}</div>
                <div style="font-size:.8em;color:#8b949e;margin-top:4px">{dominant['avg_strength']:.0%} strength</div>
                </div>""",
                unsafe_allow_html=True,
            )
        st.metric("Evidence Events", f"{total_evidence:,}")
        st.metric("Booths with Signals", total_booths)


def _render_narrative_bars(ranked: list[dict]) -> None:
    section("Narrative Strength by Type", "📊")
    labels = [NARRATIVE_META.get(r["type"], {}).get("label", r["type"]) for r in ranked[:8]]
    values = [r["avg_strength"] for r in ranked[:8]]
    colors = [NARRATIVE_META.get(r["type"], {}).get("color", "#8b949e") for r in ranked[:8]]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=colors,
            text=[f"{v:.0%}" for v in values],
            textposition="outside",
        )
    )
    fig.update_layout(
        **{
            **PLOTLY_LAYOUT,
            "height": 320,
            "xaxis": dict(range=[0, 1.1], tickformat=".0%", showgrid=True, gridcolor="#1e2d4a"),
            "yaxis": dict(autorange="reversed"),
            "margin": dict(l=0, r=60, t=20, b=20),
        },
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_emotion_breakdown(narratives: list[dict]) -> None:
    section("Emotion Breakdown", "😡")

    # Infer emotions from narrative types
    emotion_counts: dict[str, int] = {
        "anger": 0,
        "frustration": 0,
        "hope": 0,
        "support": 0,
        "neutral": 0,
    }
    for n in narratives:
        nt = n.get("narrative_type", "")
        strength = n.get("strength", 0.5)
        if nt in ("anti_incumbency", "employment_crisis", "youth_frustration"):
            emotion_counts["anger"] += int(strength * 10)
        elif nt in ("price_rise_narrative", "farmer_distress", "corruption_narrative"):
            emotion_counts["frustration"] += int(strength * 10)
        elif nt in ("development_positive", "scheme_success"):
            emotion_counts["hope"] += int(strength * 10)
        elif nt in ("swing_possible",):
            emotion_counts["support"] += int(strength * 5)
        else:
            emotion_counts["neutral"] += 3

    labels = [k.title() for k, v in emotion_counts.items() if v > 0]
    values = [v for v in emotion_counts.values() if v > 0]
    colors = [EMOTION_COLORS.get(k, "#8b949e") for k, v in emotion_counts.items() if v > 0]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            marker=dict(colors=colors, line=dict(color="#0a0e1a", width=2)),
            hole=0.45,
            textinfo="percent+label",
        )
    )
    fig.update_layout(
        **{**PLOTLY_LAYOUT, "height": 260, "showlegend": False, "margin": dict(l=0, r=0, t=10, b=0)}
    )
    st.plotly_chart(fig, use_container_width=True)

    # Dominant emotion
    dominant_emo = (
        max(emotion_counts, key=lambda k: emotion_counts[k]) if emotion_counts else "neutral"
    )
    emo_color = EMOTION_COLORS.get(dominant_emo, "#95a5a6")
    st.markdown(
        f"""<div style="background:{emo_color}22;border:1px solid {emo_color}44;
        border-radius:8px;padding:10px 14px;text-align:center;margin-top:8px">
        <span style="color:{emo_color};font-weight:700;font-size:1.05em">
        Dominant: {dominant_emo.upper()}</span>
        </div>""",
        unsafe_allow_html=True,
    )


def _render_narrative_detail(narratives: list[dict]) -> None:
    section("Narrative Details by Booth", "📋")

    if not narratives:
        st.caption("No booth-level narrative details available")
        return

    for n in sorted(narratives, key=lambda x: x.get("strength", 0), reverse=True)[:8]:
        nt = n.get("narrative_type", "unknown")
        strength = n.get("strength", 0)
        desc = n.get("description", "")
        booth_no = n.get("booth_number", "?")
        top_issues = n.get("top_issues", [])
        evidence = n.get("evidence_count", 0)
        meta = NARRATIVE_META.get(
            nt, {"icon": "🔹", "color": "#8b949e", "label": nt.replace("_", " ").title()}
        )
        bar_w = int(min(strength, 1.0) * 100)

        issues_html = ""
        if isinstance(top_issues, list) and top_issues:
            pills = "".join(
                f'<span style="background:#1e2d4a;border-radius:4px;padding:2px 6px;'
                f'font-size:.75em;margin-right:4px">{i}</span>'
                for i in top_issues[:3]
            )
            issues_html = f'<div style="margin-top:6px">{pills}</div>'

        st.markdown(
            f"""<div style="background:#0f1729;border-left:4px solid {meta['color']};
            border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:8px">
            <div style="display:flex;justify-content:space-between">
              <b>{meta['icon']} {meta['label']}</b>
              <span style="color:#8b949e;font-size:.83em">Booth {booth_no} · {evidence} events</span>
            </div>
            <div style="background:#1e2d4a;border-radius:4px;height:5px;margin:8px 0">
              <div style="background:{meta['color']};width:{bar_w}%;height:5px;border-radius:4px"></div>
            </div>
            <span style="color:{meta['color']};font-weight:700;font-size:.9em">{strength:.0%}</span>
            <span style="color:#8b949e;font-size:.85em;margin-left:8px">{desc[:100]}</span>
            {issues_html}
            </div>""",
            unsafe_allow_html=True,
        )


def _render_demo() -> None:
    st.divider()
    st.caption("📋 Demo view — run analytics.narrative_engine to see live data")

    demo_narratives = [
        {
            "narrative_type": "employment_crisis",
            "strength": 0.78,
            "evidence_count": 142,
            "description": "Youth unemployment driving negative sentiment across urban booths",
            "top_issues": ["jobs", "price_rise"],
            "booth_number": 223,
        },
        {
            "narrative_type": "anti_incumbency",
            "strength": 0.65,
            "evidence_count": 98,
            "description": "Growing frustration with ruling party over water and jobs",
            "top_issues": ["water", "governance"],
            "booth_number": 185,
        },
        {
            "narrative_type": "development_positive",
            "strength": 0.52,
            "evidence_count": 67,
            "description": "Highway and infrastructure development perceived positively",
            "top_issues": ["roads"],
            "booth_number": 201,
        },
        {
            "narrative_type": "price_rise_narrative",
            "strength": 0.71,
            "evidence_count": 115,
            "description": "Inflation and essential commodities price complaints rising sharply",
            "top_issues": ["price_rise", "farmer"],
            "booth_number": 190,
        },
        {
            "narrative_type": "scheme_success",
            "strength": 0.44,
            "evidence_count": 55,
            "description": "PM Kisan and Ujjwala scheme beneficiaries expressing positive sentiment",
            "top_issues": ["farmer", "other"],
            "booth_number": 210,
        },
    ]

    ranked = [
        {
            "type": n["narrative_type"],
            "avg_strength": n["strength"],
            "booth_count": 1,
            "evidence": n["evidence_count"],
        }
        for n in demo_narratives
    ]

    _render_top_row(ranked)
    st.divider()
    col_l, col_r = st.columns([1.3, 1])
    with col_l:
        _render_narrative_bars(ranked)
    with col_r:
        _render_emotion_breakdown(demo_narratives)
    st.divider()
    _render_narrative_detail(demo_narratives)
