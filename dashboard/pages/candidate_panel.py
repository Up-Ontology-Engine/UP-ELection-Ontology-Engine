"""Candidate Intelligence panel — affidavit, vote history, digital sentiment."""
import requests
import streamlit as st

from dashboard.components.war_room import inject_css, info_bar


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_candidates(ac_id: str, api_url: str) -> list[dict]:
    try:
        r = requests.get(f"{api_url}/ac/{ac_id}/candidates", timeout=10)
        r.raise_for_status()
        return r.json().get("candidates", [])
    except Exception:
        return []


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_ac_results(ac_id: str, api_url: str) -> list[dict]:
    """Aggregate vote totals by party from booth_results."""
    try:
        r = requests.get(f"{api_url}/ac/{ac_id}/booths", timeout=10)
        r.raise_for_status()
        return r.json().get("booths", [])
    except Exception:
        return []


def _fmt_amount(v) -> str:
    if v is None:
        return "N/A"
    v = int(v)
    if v >= 10_000_000:
        return f"₹{v/10_000_000:.1f} Cr"
    if v >= 100_000:
        return f"₹{v/100_000:.1f} L"
    return f"₹{v:,}"


# Known 2022 Gorakhpur Urban results (public ECI data, used as fallback)
_KNOWN_RESULTS = {
    "BJP": {"votes_2022": 103_390, "vote_share_2022": 62.55,
            "votes_2017": 97_000,  "vote_share_2017": 59.80},
    "SP":  {"votes_2022": 46_783,  "vote_share_2022": 28.30,
            "votes_2017": 41_000,  "vote_share_2017": 25.10},
    "BSP": {"votes_2022": 9_254,   "vote_share_2022": 5.60,
            "votes_2017": 14_000,  "vote_share_2017": 8.60},
}


def render(ac_id: str, _booth_id: str, api_url: str) -> None:
    inject_css()
    st.markdown("## 🧑 Candidate Intelligence")
    info_bar(f"AC: {ac_id}  |  Affidavit data · vote history · digital sentiment")

    candidates = _fetch_candidates(ac_id, api_url)

    if not candidates:
        st.warning("No candidate data in DB. Run seed first.")
        st.code("python -m etl.seed_known_candidates")
        _render_demo(ac_id)
        return

    candidates.sort(key=lambda c: (
        0 if c.get("is_incumbent") else 1 if c.get("is_primary_opp") else 2
    ))

    for c in candidates:
        party   = c.get("party", "")
        name    = c.get("name", "Unknown")
        is_inc  = c.get("is_incumbent")
        is_opp  = c.get("is_primary_opp")
        label   = "🔵 Ruling" if is_inc else "🔴 Opposition" if is_opp else "⚪ Others"

        with st.expander(f"{label} | {name} ({party})", expanded=bool(is_inc or is_opp)):
            _render_candidate_card(c, party)


def _render_candidate_card(c: dict, party: str) -> None:
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Affidavit Summary**")
        criminal = c.get("criminal_cases") or 0
        serious  = c.get("serious_cases") or 0
        assets   = _fmt_amount(c.get("total_assets"))
        liabs    = _fmt_amount(c.get("total_liabilities"))
        age      = c.get("age") or "N/A"
        edu      = c.get("education") or "N/A"
        crim_icon = "🔴" if criminal > 0 else "🟢"

        st.markdown(f"""
| Field | Value |
|-------|-------|
| Criminal cases | {crim_icon} {criminal} ({serious} serious) |
| Total assets | {assets} |
| Total liabilities | {liabs} |
| Age | {age} |
| Education | {edu} |
""")

    with col2:
        st.markdown("**Vote History**")
        res = _KNOWN_RESULTS.get(party, {})
        v22  = res.get("votes_2022")
        vs22 = res.get("vote_share_2022")
        v17  = res.get("votes_2017")
        vs17 = res.get("vote_share_2017")

        if v22 is not None:
            delta = ""
            if vs22 is not None and vs17 is not None:
                chg = vs22 - vs17
                delta = f" ({chg:+.1f}pp vs 2017)"
            st.markdown(f"""
| Year | Votes | Share |
|------|-------|-------|
| 2022 | {v22:,} | {vs22:.1f}%{delta} |
| 2017 | {v17:,} | {vs17:.1f}% |
""")
        else:
            st.caption("No historical data for this party")

    with col3:
        st.markdown("**Digital Sentiment**")
        score    = c.get("sentiment_score")
        mentions = c.get("mention_count") or 0
        if score is not None:
            pol = ("🟢 Positive" if score > 0.1
                   else "🔴 Negative" if score < -0.1
                   else "🟡 Neutral")
            st.markdown(f"Overall: **{pol}**")
            st.markdown(f"Score: `{score:+.3f}`")
            st.caption(f"Based on {mentions} mentions")
        else:
            st.caption("No digital signal yet")


def _render_demo(_ac_id: str) -> None:
    st.divider()
    st.caption("Demo view — seed candidate data to see live affidavit detail")

    demo = [
        {"name": "Yogi Adityanath", "party": "BJP", "is_incumbent": True, "is_primary_opp": False,
         "criminal_cases": 0, "serious_cases": 0, "total_assets": 959645, "total_liabilities": 0,
         "age": 49, "education": "M.Sc. Mathematics", "sentiment_score": 0.18, "mention_count": 1240},
        {"name": "Subhawati Upendra Dutt Shukla", "party": "SP", "is_incumbent": False, "is_primary_opp": True,
         "criminal_cases": 2, "serious_cases": 1, "total_assets": 12345000, "total_liabilities": 1500000,
         "age": 52, "education": "Graduate", "sentiment_score": -0.05, "mention_count": 312},
        {"name": "Khwaja Shamsuddin", "party": "BSP", "is_incumbent": False, "is_primary_opp": False,
         "criminal_cases": 0, "serious_cases": 0, "total_assets": 4500000, "total_liabilities": 0,
         "age": 58, "education": "Post Graduate", "sentiment_score": 0.02, "mention_count": 78},
    ]

    for c in demo:
        party  = c["party"]
        name   = c["name"]
        is_inc = c["is_incumbent"]
        is_opp = c["is_primary_opp"]
        label  = "🔵 Ruling" if is_inc else "🔴 Opposition" if is_opp else "⚪ Others"

        with st.expander(f"{label} | {name} ({party})", expanded=bool(is_inc or is_opp)):
            _render_candidate_card(c, party)
