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


def _fmt_amount(v) -> str:
    if v is None:
        return "N/A"
    v = int(v)
    if v >= 10_000_000:
        return f"₹{v/10_000_000:.2f} Cr"
    if v >= 100_000:
        return f"₹{v/100_000:.2f} L"
    return f"₹{v:,}"


def render(ac_id: str, _booth_id: str, api_url: str) -> None:
    inject_css()
    st.markdown("## 🧑 Candidate Intelligence")
    info_bar(f"AC: {ac_id}  |  Affidavit data · vote history · digital sentiment")

    candidates = _fetch_candidates(ac_id, api_url)

    if not candidates:
        st.warning("No candidate data in database for this AC.")
        st.code("python -m etl.seed_known_candidates")
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
            _render_candidate_card(c)


def _render_candidate_card(c: dict) -> None:
    # 1. Warning Badge for Incomplete Results
    completeness = c.get("result_completeness_status")
    if completeness == "winner_runnerup_only":
        st.warning("⚠️ **Partial Election Data**: Detailed non-winner breakdown is not yet finalized in the database. Omitted rows will show pending.")
    
    # 2. Key Metrics Columns
    st.markdown("### 💰 Financial Disclosures")
    m_col1, m_col2, m_col3 = st.columns(3)
    
    with m_col1:
        st.metric(
            label="Net Worth",
            value=_fmt_amount(c.get("net_worth_rs")),
            help="Computed as Total Assets - Total Liabilities"
        )
    with m_col2:
        st.metric(
            label="Total Assets",
            value=_fmt_amount(c.get("total_assets")),
            help="Movable + Immovable assets declared in affidavit"
        )
    with m_col3:
        st.metric(
            label="Total Liabilities",
            value=_fmt_amount(c.get("total_liabilities")),
            help="Debts, loans, and other liabilities declared in affidavit"
        )

    # 3. Dynamic Tabs for Details
    tab_summary, tab_assets, tab_history, tab_sentiment = st.tabs([
        "📋 Profile & Summary",
        "💎 Detailed Asset Breakdown",
        "⏱️ Contesting History",
        "📈 Digital Sentiment"
    ])
    
    with tab_summary:
        st.markdown("**Candidate Profile**")
        criminal = c.get("criminal_cases") or 0
        serious  = c.get("serious_cases") or 0
        age      = c.get("age") or "N/A"
        edu      = c.get("education") or "N/A"
        prof     = c.get("self_profession") or "N/A"
        enroll   = c.get("voter_enrolled_ac_name") or "N/A"
        
        crim_icon = "🔴" if criminal > 0 else "🟢"
        
        st.markdown(f"""
| Field | Value |
|-------|-------|
| **Age** | {age} years |
| **Education** | {edu} |
| **Declared Profession** | {prof} |
| **Voter Enrollment Constituency** | {enroll} |
| **Criminal Records** | {crim_icon} {criminal} cases ({serious} serious) |
""")
        
        if c.get("source_affidavit_url"):
            st.link_button("🔗 View Original Affidavit PDF", c["source_affidavit_url"])

    with tab_assets:
        # Movable and Immovable breakdowns
        col_mov, col_imm = st.columns(2)
        
        with col_mov:
            st.markdown("**Movable Assets Breakdown**")
            movable_items = c.get("movable_assets_json") or []
            if movable_items:
                mov_rows = []
                for item in movable_items:
                    val = item.get("total_rs") or item.get("value_rs") or 0
                    if val > 0:
                        mov_rows.append({"Asset Type": item.get("item", "Other"), "Value": _fmt_amount(val)})
                if mov_rows:
                    st.dataframe(mov_rows, use_container_width=True, hide_index=True)
                else:
                    st.caption("No positive movable assets listed.")
            else:
                st.caption("No movable breakdown available.")
                
        with col_imm:
            st.markdown("**Immovable Assets Breakdown**")
            immovable_items = c.get("immovable_assets_json") or []
            if immovable_items:
                imm_rows = []
                for item in immovable_items:
                    val = item.get("total_rs") or item.get("value_rs") or 0
                    if val > 0:
                        imm_rows.append({"Property Type": item.get("item", "Other"), "Value": _fmt_amount(val)})
                if imm_rows:
                    st.dataframe(imm_rows, use_container_width=True, hide_index=True)
                else:
                    st.caption("No positive immovable assets listed.")
            else:
                st.caption("No immovable breakdown available.")

        # ITR Income Disclosures
        itr_items = c.get("itr_income_json") or []
        if itr_items:
            st.markdown("**ITR Income Disclosures**")
            itr_rows = []
            for item in itr_items:
                year = item.get("year")
                rel = item.get("relation", "self")
                inc = item.get("total_income_rs")
                if inc is not None:
                    itr_rows.append({"Assessment Year": year, "Disclosed By": rel.capitalize(), "Annual Income": _fmt_amount(inc)})
            if itr_rows:
                st.dataframe(itr_rows, use_container_width=True, hide_index=True)

    with tab_history:
        st.markdown("**Dynamic Contest History**")
        history = c.get("history_json") or []
        if history:
            history_rows = []
            for h in history:
                year = h.get("election_year")
                constituency = h.get("constituency")
                party_id = h.get("party_id")
                votes = h.get("votes_received")
                share = h.get("vote_share")
                is_winner = h.get("is_winner")
                etype = h.get("election_type", "Vidhan Sabha")
                
                votes_str = f"{votes:,}" if votes is not None else "Pending"
                share_str = f"{share:.2f}%" if share is not None else "Pending"
                status_str = "🏆 Won" if is_winner else "Runner-up" if h.get("result_position_label") == "runner_up" else "Contested"
                
                history_rows.append({
                    "Year": year,
                    "Type": etype,
                    "Constituency": constituency,
                    "Party": party_id,
                    "Votes": votes_str,
                    "Vote Share": share_str,
                    "Result": status_str
                })
            
            st.dataframe(history_rows, use_container_width=True, hide_index=True)
        else:
            st.caption("No contest history found in the database.")

    with tab_sentiment:
        st.markdown("**Digital Signal Analysis (Past 30 Days)**")
        score    = c.get("sentiment_score")
        mentions = c.get("mention_count") or 0
        if score is not None and mentions > 0:
            pol = ("🟢 Positive" if score > 0.1
                   else "🔴 Negative" if score < -0.1
                   else "🟡 Neutral")
            st.markdown(f"Overall Digital Sentiment: **{pol}**")
            st.markdown(f"Sentiment Score: `{score:+.3f}`")
            st.caption(f"Based on {mentions} live mentions in YouTube comments and news articles.")
        else:
            st.caption("No digital signal yet. Keep collecting comments and news to see sentiment analytics.")
