"""Candidate affidavit comparison panel."""
import requests, streamlit as st
import plotly.graph_objects as go


@st.cache_data(ttl=300)
def _fetch_candidates(ac_id: str, api_url: str):
    try:
        r = requests.get(f"{api_url}/ac/{ac_id}/candidates", timeout=10)
        r.raise_for_status()
        return r.json().get("candidates", [])
    except Exception:
        return []


def _fmt_amount(v) -> str:
    if v is None: return "N/A"
    v = int(v)
    if v >= 10_000_000: return f"₹{v/10_000_000:.1f} Cr"
    if v >= 100_000:    return f"₹{v/100_000:.1f} L"
    return f"₹{v:,}"


def render(ac_id: str, booth_id: str, api_url: str):
    st.title("🏛️ Candidate Profiles")
    st.caption(f"Affidavit data + digital sentiment — {ac_id}")

    candidates = _fetch_candidates(ac_id, api_url)
    if not candidates:
        st.warning("No candidate data. Run: `python -m ingestion.myneta_candidates`")
        return

    # Sort: incumbent first, then primary opposition, then others
    candidates.sort(key=lambda c: (
        0 if c.get("is_incumbent") else 1 if c.get("is_primary_opp") else 2
    ))

    for c in candidates:
        party   = c.get("party", "")
        name    = c.get("name", "")
        is_inc  = c.get("is_incumbent")
        is_opp  = c.get("is_primary_opp")
        label   = "🔵 Ruling" if is_inc else "🔴 Opposition" if is_opp else "Others"
        color   = "#FF6B35" if is_inc else "#3498db" if is_opp else "#95a5a6"

        with st.expander(f"{label} | {name} ({party})", expanded=is_inc or is_opp):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Affidavit Summary**")
                criminal = c.get("criminal_cases", 0) or 0
                serious  = c.get("serious_cases", 0) or 0
                assets   = _fmt_amount(c.get("total_assets"))
                liabs    = _fmt_amount(c.get("total_liabilities"))
                age      = c.get("age", "?")
                edu      = c.get("education", "N/A")

                crim_color = "🔴" if criminal > 0 else "🟢"
                st.markdown(f"""
| Field | Value |
|-------|-------|
| Criminal cases | {crim_color} {criminal} ({serious} serious) |
| Total assets | {assets} |
| Total liabilities | {liabs} |
| Age | {age} |
| Education | {edu} |
""")

            with col2:
                score = c.get("sentiment_score")
                mentions = c.get("mention_count", 0)
                if score is not None:
                    st.markdown("**Digital Sentiment**")
                    pol = "🟢 Positive" if score > 0.1 else "🔴 Negative" if score < -0.1 else "🟡 Neutral"
                    st.markdown(f"Overall: **{pol}** (`{score:+.3f}`)")
                    st.caption(f"Based on {mentions} mentions")
                else:
                    st.caption("No digital sentiment data yet")
