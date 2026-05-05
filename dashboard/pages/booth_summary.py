"""
Booth 223-style summary card — the primary analyst view.

Renders:
  🗳️ Historical results
  📊 Digital lean
  ⚠️ Data confidence
  🔥 Top issues with momentum
  🏛️ Candidate insights
  📉 Scheme gap analysis
  🧠 Key insight
  📌 Recommendation
"""
from __future__ import annotations
import requests
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px


POLARITY_EMOJI = {1: "✅", -1: "❌", 0: "➖"}
POLARITY_COLOR = {1: "#2ecc71", -1: "#e74c3c", 0: "#95a5a6"}
CONFIDENCE_COLOR = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🟠", "INSUFFICIENT": "🔴", "UNKNOWN": "⚪"}


@st.cache_data(ttl=120, show_spinner=False)
def _fetch_summary(booth_id: str, days: int, api_url: str) -> dict | None:
    try:
        r = requests.get(f"{api_url}/booth/{booth_id}/summary",
                         params={"days": days}, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return None


@st.cache_data(ttl=120, show_spinner=False)
def _fetch_candidates(ac_id: str, api_url: str) -> list[dict]:
    try:
        r = requests.get(f"{api_url}/ac/{ac_id}/candidates", timeout=10)
        r.raise_for_status()
        return r.json().get("candidates", [])
    except Exception:
        return []


def render(booth_id: str, window_days: int, api_url: str):
    with st.spinner("Loading booth intelligence..."):
        data = _fetch_summary(booth_id, window_days, api_url)

    if not data:
        st.error("Could not load booth data. Is the API running?")
        st.code(f"Start: uvicorn api.main:app --reload")
        return

    # ── Header ────────────────────────────────────────────────────────────────
    booth_num = data.get("booth_number", "?")
    booth_name = data.get("name", "Unknown")
    ac_name = data.get("ac_name", "Gorakhpur Urban")

    st.title(f"Booth {booth_num} — {ac_name}")
    st.caption(f"📍 {booth_name}")

    voters = data.get("total_voters", 0)
    male   = data.get("male_voters", 0)
    female = data.get("female_voters", 0)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Voters", f"{voters:,}")
    col2.metric("Male", f"{male:,}")
    col3.metric("Female", f"{female:,}")

    st.divider()

    # ── Row 1: Historical | Digital Lean | Confidence ─────────────────────────
    c1, c2, c3 = st.columns([1.2, 1.2, 0.8])

    with c1:
        _render_historical(data.get("historical", {}))

    with c2:
        _render_digital_lean(data.get("digital_pulse", {}))

    with c3:
        _render_confidence(data.get("confidence", {}))

    st.divider()

    # ── Row 2: Top Issues | Candidate Insights ────────────────────────────────
    c4, c5 = st.columns([1.2, 1.2])

    with c4:
        _render_top_issues(data.get("top_issues", []), data.get("issue_momentum", {}))

    with c5:
        _render_candidate_insights(
            data.get("digital_pulse", {}).get("pulse_detail", []),
            booth_id, api_url
        )

    st.divider()

    # ── Row 2b: Data Quality reasons ─────────────────────────────────────────
    _render_data_quality(data.get("data_quality"))

    st.divider()

    # ── Row 3: Scheme Analysis | Narratives ───────────────────────────────────
    c6, c7 = st.columns([1, 1])

    with c6:
        _render_scheme_analysis(data.get("scheme_analysis", []))

    with c7:
        _render_narratives(data.get("narratives", []))

    st.divider()

    # ── Row 4: Contradiction Flags | Key Insight ──────────────────────────────
    c8, c9 = st.columns([1, 1])

    with c8:
        _render_contradictions(data.get("contradictions", []))

    with c9:
        _render_insight_box(data.get("key_insight", ""), data.get("recommendation", ""))

    st.divider()

    # ── Backing Comments ───────────────────────────────────────────────────────
    _render_comments(data.get("backing_comments", []))


# ── Sub-renderers ─────────────────────────────────────────────────────────────

def _render_historical(hist: dict):
    st.markdown("### 🗳️ Historical Results")
    wins  = hist.get("bjp_won_count", 0)
    shares = hist.get("bjp_vote_shares", [])
    trend  = hist.get("trend", "unknown")

    if not shares:
        st.caption("No historical data available")
        return

    if wins >= 1:
        win_text = f"BJP won last {wins} election{'s' if wins > 1 else ''}"
        st.success(win_text)
    else:
        st.warning("BJP has not won recently")

    if len(shares) >= 2:
        share_str = " → ".join(f"{s:.0f}%" for s in shares)
        trend_icon = "📉" if trend == "declining" else "📈" if trend == "rising" else "➡️"
        st.markdown(f"**Vote share:** {share_str} {trend_icon}")
        st.caption(f"Trend: {trend.capitalize()}")

    # Mini chart if multiple years
    full = hist.get("full_history", [])
    bjp_hist = [(h["election_year"], h["vote_share"])
                for h in full if h["party"] in ("BJP","भाजपा") and h["vote_share"]]
    if len(bjp_hist) >= 2:
        years, vs = zip(*bjp_hist)
        fig = go.Figure(go.Scatter(
            x=list(years), y=list(vs), mode="lines+markers+text",
            text=[f"{v:.0f}%" for v in vs], textposition="top center",
            line=dict(color="#FF6B35", width=2),
            marker=dict(size=8, color="#FF6B35"),
        ))
        fig.update_layout(
            height=150, margin=dict(l=0, r=0, t=10, b=20),
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, range=[0, 100]),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)


def _render_digital_lean(pulse: dict):
    st.markdown("### 📊 Current Digital Lean")
    lean_label = pulse.get("lean_label", "Insufficient data")
    bjp   = pulse.get("bjp_pulse", 0) or 0
    opp   = pulse.get("opp_pulse", 0) or 0
    lean  = pulse.get("digital_lean", 0) or 0

    color = "#FF6B35" if "BJP" in lean_label else "#3498db" if "Opp" in lean_label else "#95a5a6"
    st.markdown(
        f"""<div style="background:{color}22;border-left:4px solid {color};
        padding:12px;border-radius:6px;font-size:1.2em;font-weight:bold;">
        {lean_label}</div>""",
        unsafe_allow_html=True,
    )

    if bjp != 0 or opp != 0:
        fig = go.Figure()
        fig.add_bar(name="BJP", x=["BJP"], y=[round(bjp, 3)],
                    marker_color="#FF6B35", text=[f"{bjp:+.2f}"], textposition="auto")
        fig.add_bar(name="Opposition", x=["Opposition"], y=[round(opp, 3)],
                    marker_color="#3498db", text=[f"{opp:+.2f}"], textposition="auto")
        fig.update_layout(
            height=180, margin=dict(l=0, r=0, t=10, b=20),
            yaxis=dict(range=[-1, 1], zeroline=True, zerolinecolor="#666"),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"BJP: {bjp:+.3f} | Opp: {opp:+.3f} | Lean: {lean:+.3f}")
    else:
        st.caption("No pulse events mapped to this booth yet.")


def _render_confidence(conf: dict):
    st.markdown("### ⚠️ Confidence")
    label  = conf.get("label", "UNKNOWN")
    score  = conf.get("score") or 0
    events = conf.get("event_count", 0)

    icon = CONFIDENCE_COLOR.get(label, "⚪")
    st.markdown(f"## {icon} {label}")
    st.metric("Events", events)
    if score:
        st.caption(f"Avg confidence: {score:.2f}")

    reasons = []
    if events < 20:
        reasons.append("Limited digital data")
    if label in ("LOW", "INSUFFICIENT"):
        reasons.append("Few booth-mapped events")
    if reasons:
        for r in reasons:
            st.caption(f"⚠️ {r}")


def _render_top_issues(issues: list[dict], momentum: dict):
    st.markdown("### 🔥 Top Issues")
    if not issues:
        st.caption("No issue data yet")
        return

    for i, issue in enumerate(issues[:5], 1):
        code    = issue.get("issue", "")
        count   = issue.get("mention_count", 0)
        polarity = issue.get("avg_polarity", 0)
        mom     = momentum.get(code)

        icon = POLARITY_EMOJI.get(1 if polarity > 0.1 else (-1 if polarity < -0.1 else 0), "➖")
        mom_text = ""
        if mom is not None:
            sign = "+" if mom > 0 else ""
            mom_text = f"&nbsp;&nbsp;<span style='color:{'#e74c3c' if mom > 0 else '#2ecc71'}'>{sign}{mom*100:.0f}%</span>"

        label = code.replace("_", " ").title()
        bar_width = min(int((count / max(i["mention_count"] for i in issues)) * 100), 100)

        st.markdown(
            f"""<div style="margin-bottom:8px">
            <b>{i}. {label}</b> {icon}{mom_text}
            <div style="background:#eee;border-radius:4px;height:8px;margin-top:4px">
              <div style="background:#FF6B35;width:{bar_width}%;height:8px;border-radius:4px"></div>
            </div>
            <small style="color:#888">{count} mentions</small>
            </div>""",
            unsafe_allow_html=True,
        )


def _render_candidate_insights(pulse_detail: list, booth_id: str, api_url: str):
    st.markdown("### 🏛️ Candidate Insights")

    party_pulse = {p["entity"]: p for p in pulse_detail}

    # BJP section
    bjp_pulse = party_pulse.get("BJP") or party_pulse.get("Yogi Adityanath")
    if bjp_pulse:
        score = bjp_pulse.get("pulse_score", 0) or 0
        icon  = "📈" if score > 0 else "📉" if score < 0 else "➡️"
        st.markdown(f"**BJP** {icon} `{score:+.3f}`")

        # Try to get issue-level breakdown
        try:
            r = requests.get(f"{api_url}/booth/{booth_id}/issues", timeout=5)
            if r.ok:
                all_issues = r.json().get("issues", [])
                pos_issues = [i["issue"].replace("_"," ") for i in all_issues if (i.get("avg_polarity") or 0) > 0]
                neg_issues = [i["issue"].replace("_"," ") for i in all_issues if (i.get("avg_polarity") or 0) < -0.1]
                if pos_issues:
                    st.markdown(f"&nbsp;&nbsp;✅ Positive: {', '.join(pos_issues[:2])}")
                if neg_issues:
                    st.markdown(f"&nbsp;&nbsp;❌ Negative: {', '.join(neg_issues[:2])}")
        except Exception:
            pass
    else:
        st.caption("No BJP pulse data")

    st.markdown("")

    # Opposition section
    opp_entities = [e for e in ["SP", "BSP", "Congress", "Akhilesh Yadav"] if e in party_pulse]
    if opp_entities:
        for ent in opp_entities[:2]:
            p = party_pulse[ent]
            score = p.get("pulse_score", 0) or 0
            icon  = "📈" if score > 0 else "📉" if score < 0 else "➡️"
            st.markdown(f"**{ent}** {icon} `{score:+.3f}`")
    else:
        st.caption("No opposition pulse data")


def _render_data_quality(quality: dict | None):
    if not quality:
        return
    label   = quality.get("quality_label", "UNKNOWN")
    score   = quality.get("overall_quality_score") or 0
    reasons = quality.get("quality_reasons") or []
    events  = quality.get("total_events", 0)
    sources = quality.get("unique_sources", 0)

    icon = CONFIDENCE_COLOR.get(label, "⚪")
    color_map = {"HIGH": "#2ecc71", "MEDIUM": "#f39c12", "LOW": "#e67e22",
                 "INSUFFICIENT": "#e74c3c", "UNKNOWN": "#95a5a6"}
    color = color_map.get(label, "#95a5a6")

    cols = st.columns([2, 3])
    with cols[0]:
        st.markdown("### 📋 Data Quality")
        st.markdown(
            f"""<div style="background:{color}22;border-left:4px solid {color};
            padding:10px;border-radius:6px">
            <b>{icon} {label}</b><br>
            <small>Score: {score:.2f} &nbsp;|&nbsp;
            {events} events &nbsp;|&nbsp; {sources} sources</small>
            </div>""",
            unsafe_allow_html=True,
        )
    with cols[1]:
        if reasons:
            st.markdown("**Why this confidence level:**")
            for r in reasons:
                st.caption(f"⚠️ {r}")
        else:
            st.caption("No quality issues detected.")

        # Source composition mini-bar
        src_data = {
            "YouTube":    quality.get("youtube_pct", 0),
            "News":       quality.get("news_pct", 0),
            "Survey":     quality.get("survey_pct", 0),
            "Field Note": quality.get("field_note_pct", 0),
        }
        total = sum(src_data.values())
        if total > 0:
            parts = " | ".join(
                f"{k}: {v:.0f}%" for k, v in src_data.items() if v > 0
            )
            st.caption(f"Sources — {parts}")


def _render_narratives(narratives: list):
    st.markdown("### 🧩 Detected Narratives")
    if not narratives:
        st.caption("No strong narrative patterns detected in this window")
        return

    NARRATIVE_ICON = {
        "development_positive":   "🏗️",
        "anti_incumbency":        "📣",
        "corruption_narrative":   "🔍",
        "price_rise_narrative":   "💸",
        "women_safety_narrative": "🛡️",
        "employment_crisis":      "💼",
        "scheme_success":         "✅",
        "swing_possible":         "⚖️",
    }
    NARRATIVE_COLOR = {
        "development_positive": "#2ecc71",
        "anti_incumbency":      "#e74c3c",
        "corruption_narrative": "#e67e22",
        "price_rise_narrative": "#f39c12",
        "swing_possible":       "#9b59b6",
    }

    for n in narratives[:4]:
        ntype  = n.get("narrative_type", "")
        strength = n.get("strength", 0)
        desc   = n.get("description", "")
        icon   = NARRATIVE_ICON.get(ntype, "🔹")
        color  = NARRATIVE_COLOR.get(ntype, "#3498db")
        label  = ntype.replace("_", " ").title()
        bar_w  = int(min(strength, 1.0) * 100)

        st.markdown(
            f"""<div style="background:{color}11;border-left:3px solid {color};
            padding:8px 12px;border-radius:4px;margin-bottom:8px">
            <b>{icon} {label}</b>
            <span style="float:right;color:{color};font-weight:bold">
              {strength:.0%}
            </span><br>
            <div style="background:#eee;border-radius:4px;height:5px;margin:4px 0">
              <div style="background:{color};width:{bar_w}%;height:5px;border-radius:4px">
              </div>
            </div>
            <small style="color:#555">{desc[:120]}</small>
            </div>""",
            unsafe_allow_html=True,
        )


def _render_contradictions(contradictions: list):
    st.markdown("### ⚡ Signal Conflicts")
    if not contradictions:
        st.success("No cross-source contradictions detected")
        return

    mixed = [c for c in contradictions if c.get("flag_label") == "MIXED_SIGNALS"]
    swing = [c for c in contradictions if c.get("flag_label") == "SWING_INDICATOR"]

    if mixed:
        st.warning(f"⚠️ **{len(mixed)} MIXED SIGNAL{'S' if len(mixed) > 1 else ''}** — sources disagree strongly")

    show = (mixed + swing)[:5]
    for c in show:
        entity  = c.get("entity", "")
        src_a   = c.get("source_a", "")
        src_b   = c.get("source_b", "")
        pol_a   = c.get("polarity_a") or 0
        pol_b   = c.get("polarity_b") or 0
        delta   = c.get("delta") or 0
        label   = c.get("flag_label", "")

        label_color = "#e74c3c" if label == "MIXED_SIGNALS" else "#f39c12"
        st.markdown(
            f"""<div style="background:{label_color}11;border-left:3px solid {label_color};
            padding:6px 10px;border-radius:4px;margin-bottom:6px;font-size:0.9em">
            <b>{entity}</b> &nbsp;
            <span style="color:#888">{src_a}: {pol_a:+.2f} vs
            {src_b}: {pol_b:+.2f} (Δ {delta:.2f})</span>
            </div>""",
            unsafe_allow_html=True,
        )


def _render_scheme_analysis(scheme_gaps: list):
    st.markdown("### 📉 Scheme Analysis")
    if not scheme_gaps:
        st.caption("No scheme data linked to this booth yet")
        return

    GAP_COLOR = {
        "execution_gap":   "#e74c3c",
        "reach_gap":       "#e67e22",
        "awareness_gap":   "#f39c12",
        "performing_well": "#2ecc71",
        "in_progress":     "#3498db",
        "no_data":         "#95a5a6",
    }
    GAP_ICON = {
        "execution_gap":   "⚠️",
        "reach_gap":       "📍",
        "awareness_gap":   "💬",
        "performing_well": "✅",
        "in_progress":     "🔄",
        "no_data":         "❓",
    }

    for scheme in scheme_gaps[:5]:
        name      = scheme.get("scheme_name", "")
        gap_type  = scheme.get("gap_type") or "no_data"
        gap_label = scheme.get("gap_label", "")
        priority  = scheme.get("priority", "LOW")
        bcount    = scheme.get("beneficiary_count") or 0

        color  = GAP_COLOR.get(gap_type, "#95a5a6")
        icon   = GAP_ICON.get(gap_type, "❓")
        pri_badge = ("🔴 HIGH" if priority == "HIGH"
                     else "🟡 MEDIUM" if priority == "MEDIUM" else "🟢 LOW")

        st.markdown(
            f"""<div style="background:{color}11;border-left:3px solid {color};
            padding:8px 12px;border-radius:4px;margin-bottom:6px">
            {icon} <b>{name}</b> &nbsp;
            <span style="float:right;font-size:0.8em">{pri_badge}</span><br>
            <small style="color:#555">{gap_label[:100]}</small><br>
            <small style="color:#888">{bcount:,} beneficiaries</small>
            </div>""",
            unsafe_allow_html=True,
        )


def _render_insight_box(insight: str, recommendation: str):
    st.markdown("### 🧠 Key Insight")
    if insight:
        st.info(insight)
    else:
        st.caption("Not enough data for automated insight")

    st.markdown("### 📌 Recommendation")
    if recommendation:
        st.success(recommendation)
    else:
        st.caption("Collect more data to generate recommendations")


def _render_comments(comments: list):
    if not comments:
        return

    st.markdown("### 💬 Backing Evidence")
    st.caption("High-confidence pulse events that drove the above scores")

    for c in comments[:8]:
        polarity = c.get("polarity", 0)
        entity   = c.get("entity", "")
        issue    = (c.get("issue") or "").replace("_", " ")
        conf     = c.get("confidence", 0) or 0
        source   = c.get("source", "")
        text     = c.get("text_raw", "")[:250]

        border = POLARITY_COLOR.get(polarity, "#95a5a6")
        pol_icon = POLARITY_EMOJI.get(polarity, "➖")

        tag = f"{entity}" + (f" / {issue}" if issue else "")
        src_icon = "▶️" if source == "youtube" else "📰" if source == "news" else "📋"

        st.markdown(
            f"""<div style="border-left:3px solid {border};padding:8px 12px;
            margin-bottom:8px;background:{border}11;border-radius:0 6px 6px 0">
            <div style="font-size:0.85em;color:#666;margin-bottom:4px">
              {pol_icon} {tag} &nbsp;·&nbsp; {src_icon} {source} &nbsp;·&nbsp;
              conf: {conf:.2f}
            </div>
            <div style="font-size:0.95em">{text}…</div>
            </div>""",
            unsafe_allow_html=True,
        )
