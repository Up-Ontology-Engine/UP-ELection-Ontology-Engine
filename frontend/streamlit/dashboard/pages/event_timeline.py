"""
Page 6 — Event Timeline
Chronological political events with sentiment impact overlay.
"""

from __future__ import annotations

import plotly.graph_objects as go
import requests
import streamlit as st

from dashboard.components.war_room import PLOTLY_LAYOUT, info_bar, inject_css, section

EVENT_TYPE_META = {
    "rally": {"icon": "🎤", "color": "#3498db"},
    "protest": {"icon": "✊", "color": "#e74c3c"},
    "government_announcement": {"icon": "📢", "color": "#FF6B35"},
    "crime": {"icon": "🚨", "color": "#e74c3c"},
    "scheme_launch": {"icon": "🚀", "color": "#2ecc71"},
    "controversy": {"icon": "🔥", "color": "#e67e22"},
    "election": {"icon": "🗳️", "color": "#FF6B35"},
    "scam": {"icon": "💰", "color": "#e74c3c"},
    "infrastructure": {"icon": "🏗️", "color": "#3498db"},
    "other": {"icon": "📌", "color": "#8b949e"},
}


@st.cache_data(ttl=120, show_spinner=False)
def _fetch_events(ac_id: str, api_url: str) -> list[dict]:
    try:
        r = requests.get(f"{api_url}/ac/{ac_id}/events", timeout=10)
        r.raise_for_status()
        return r.json().get("events", [])
    except Exception:
        return []


def render(ac_id: str, ac_name: str, api_url: str) -> None:
    inject_css()

    st.markdown("## 📅 Event Timeline")
    info_bar(f"AC: {ac_name}  |  Chronological events that shaped constituency sentiment")

    c1, c2, c3 = st.columns(3)
    with c1:
        event_type_filter = st.multiselect(
            "Event type",
            options=list(EVENT_TYPE_META.keys()),
            default=[],
            placeholder="All types",
        )
    with c2:
        party_filter = st.selectbox("Party impact", ["All", "BJP", "SP", "BSP", "INC"])
    with c3:
        sentiment_filter = st.selectbox("Sentiment", ["All", "Positive", "Negative", "Mixed"])

    events = _fetch_events(ac_id, api_url)

    if not events:
        st.warning("No event data loaded yet.")
        st.code(
            "Run: python -m ingestion.political_events  OR  populate the political_events table"
        )
        _render_demo(ac_name)
        return

    # Apply filters
    filtered = events
    if event_type_filter:
        filtered = [e for e in filtered if e.get("event_type") in event_type_filter]
    if party_filter != "All":
        filtered = [
            e
            for e in filtered
            if party_filter.lower() in (e.get("parties_mentioned") or "").lower()
        ]
    if sentiment_filter != "All":
        tag = {"Positive": "positive", "Negative": "negative", "Mixed": "mixed"}[sentiment_filter]
        filtered = [e for e in filtered if (e.get("sentiment_impact") or "").lower() == tag]

    if not filtered:
        st.info("No events match the current filters.")
        return

    _render_summary(events, filtered)
    st.divider()
    _render_sentiment_chart(filtered)
    st.divider()
    _render_timeline(filtered)


def _render_summary(all_events: list[dict], filtered: list[dict]) -> None:
    total = len(all_events)
    showing = len(filtered)
    bjp_pos = sum(
        1
        for e in filtered
        if "bjp" in (e.get("parties_mentioned") or "").lower()
        and (e.get("sentiment_impact") or "") == "positive"
    )
    negative = sum(1 for e in filtered if (e.get("sentiment_impact") or "") == "negative")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Events", total)
    c2.metric("Showing", showing)
    c3.metric("BJP Positive", bjp_pos)
    c4.metric("Negative Events", negative)


def _render_sentiment_chart(events: list[dict]) -> None:
    section("Sentiment Impact Timeline", "📈")

    dates = [e.get("event_date") or e.get("created_at", "")[:10] for e in events]
    impacts = []
    for e in events:
        si = (e.get("sentiment_impact") or "").lower()
        impacts.append(1 if si == "positive" else -1 if si == "negative" else 0)

    if not any(d for d in dates):
        st.caption("No date data available for chart")
        return

    # Cumulative sentiment score
    cumulative = []
    running = 0
    for i in impacts:
        running += i
        cumulative.append(running)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=cumulative,
            mode="lines+markers",
            fill="tonexty" if min(cumulative, default=0) >= 0 else "tozeroy",
            line=dict(color="#FF6B35", width=2),
            marker=dict(
                size=8,
                color=[
                    "#2ecc71" if v > 0 else "#e74c3c" if v < 0 else "#95a5a6" for v in cumulative
                ],
            ),
            name="Cumulative Sentiment",
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color="#8b949e", line_width=1)
    fig.update_layout(
        **{
            **PLOTLY_LAYOUT,
            "height": 220,
            "xaxis": dict(showgrid=False),
            "yaxis": dict(showgrid=True, gridcolor="#1e2d4a", title="Cumulative Impact"),
            "margin": dict(l=0, r=0, t=20, b=20),
        },
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_timeline(events: list[dict]) -> None:
    section("Events", "📌")

    # Sort by date descending
    sorted_events = sorted(
        events,
        key=lambda e: e.get("event_date") or e.get("created_at", ""),
        reverse=True,
    )

    for e in sorted_events[:30]:
        etype = e.get("event_type", "other")
        date_str = (e.get("event_date") or e.get("created_at", ""))[:10]
        title = e.get("title", e.get("event_description", "")[:80])
        desc = e.get("description") or e.get("event_description", "")
        parties = e.get("parties_mentioned", "")
        si = (e.get("sentiment_impact") or "").lower()
        location = e.get("location_hint") or e.get("ac_id", "")

        meta = EVENT_TYPE_META.get(etype, EVENT_TYPE_META["other"])
        icon = meta["icon"]
        color = meta["color"]

        si_color = {"positive": "#2ecc71", "negative": "#e74c3c", "mixed": "#f39c12"}.get(
            si, "#8b949e"
        )
        si_icon = {"positive": "📈", "negative": "📉", "mixed": "↔️"}.get(si, "➖")

        parties_html = ""
        if parties:
            for party in str(parties).split(","):
                p = party.strip()
                if p:
                    pc = {"BJP": "#FF6B35", "SP": "#3498db", "BSP": "#9b59b6"}.get(
                        p.upper(), "#8b949e"
                    )
                    parties_html += (
                        f'<span style="background:{pc}33;color:{pc};border-radius:4px;'
                        f'padding:1px 6px;font-size:.75em;margin-right:3px">{p}</span>'
                    )

        st.markdown(
            f"""<div class="tl-node">
            <div style="display:flex;justify-content:space-between;align-items:flex-start">
              <div>
                <span style="font-size:1.2em">{icon}</span>
                <b style="margin-left:6px">{title}</b>
              </div>
              <div style="text-align:right;white-space:nowrap;margin-left:8px">
                <span style="color:{si_color};font-size:.85em">{si_icon} {si.title() if si else 'Unknown'}</span>
                <br><span style="color:#8b949e;font-size:.78em">{date_str}</span>
              </div>
            </div>
            <div style="margin-top:6px;color:#8b949e;font-size:.87em">{(desc or '')[:180]}</div>
            <div style="margin-top:6px;display:flex;gap:6px;align-items:center;flex-wrap:wrap">
              {parties_html}
              {f'<span style="color:#8b949e;font-size:.78em">📍 {location}</span>' if location else ''}
            </div>
            </div>""",
            unsafe_allow_html=True,
        )


def _render_demo(ac_name: str) -> None:
    st.divider()
    st.caption("📋 Demo view — populate political_events table to see live data")

    demo_events = [
        {
            "event_type": "rally",
            "event_date": "2024-01-15",
            "title": "CM Yogi Rally at Gorakhpur",
            "event_description": "Massive rally by Chief Minister ahead of election season",
            "parties_mentioned": "BJP",
            "sentiment_impact": "positive",
            "location_hint": "Gorakhpur Urban",
        },
        {
            "event_type": "protest",
            "event_date": "2024-01-08",
            "title": "Water Shortage Protest",
            "event_description": "Citizens protested acute water shortage in urban areas",
            "parties_mentioned": "SP",
            "sentiment_impact": "negative",
            "location_hint": "Rustampur",
        },
        {
            "event_type": "government_announcement",
            "event_date": "2024-01-12",
            "title": "AIIMS Gorakhpur Phase-II Announced",
            "event_description": "Government announces expansion of AIIMS Gorakhpur campus",
            "parties_mentioned": "BJP",
            "sentiment_impact": "positive",
            "location_hint": "Gorakhpur",
        },
        {
            "event_type": "controversy",
            "event_date": "2024-01-18",
            "title": "Paper Leak Controversy Resurfaces",
            "event_description": "Opposition raises paper leak issue, targets youth vote",
            "parties_mentioned": "SP,BSP",
            "sentiment_impact": "negative",
            "location_hint": "",
        },
        {
            "event_type": "scheme_launch",
            "event_date": "2024-01-20",
            "title": "Jal Jeevan Mission Progress Review",
            "event_description": "District administration reviews JJM implementation; 60% coverage achieved",
            "parties_mentioned": "BJP",
            "sentiment_impact": "mixed",
            "location_hint": "",
        },
        {
            "event_type": "protest",
            "event_date": "2024-01-22",
            "title": "Farmer Protest on Sugarcane Price",
            "event_description": "Farmers demand increase in sugarcane MSP, block highway briefly",
            "parties_mentioned": "SP",
            "sentiment_impact": "negative",
            "location_hint": "Khajani Road",
        },
    ]

    _render_summary(demo_events, demo_events)
    st.divider()
    _render_sentiment_chart(demo_events)
    st.divider()
    _render_timeline(demo_events)
