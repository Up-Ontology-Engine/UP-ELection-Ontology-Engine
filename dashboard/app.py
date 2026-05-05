"""
Gorakhpur KG — Analyst Dashboard
Entry point: streamlit run dashboard/app.py
"""
import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Gorakhpur KG — Booth Intelligence",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Flag_of_Uttar_Pradesh.svg/200px-Flag_of_Uttar_Pradesh.svg.png", width=60)
    st.title("Gorakhpur KG")
    st.caption("Booth-level political intelligence")
    st.divider()

    AC_ID   = os.environ.get("PILOT_AC_ID", "GKP_URBAN")
    API_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

    # Load booth list
    import requests as req

    @st.cache_data(ttl=300)
    def load_booths(ac_id: str):
        try:
            r = req.get(f"{API_URL}/ac/{ac_id}/booths", timeout=10)
            r.raise_for_status()
            return r.json().get("booths", [])
        except Exception as e:
            st.warning(f"Could not load booths: {e}")
            return []

    booths = load_booths(AC_ID)

    if not booths:
        st.error("No booth data available. Run ingestion first.")
        st.stop()

    # Build dropdown options
    booth_options = {
        f"Booth {b['booth_number']} — {b['name'][:40]}": b["booth_id"]
        for b in booths if b.get("booth_number")
    }
    selected_label = st.selectbox(
        "Select Booth",
        options=list(booth_options.keys()),
        help="Select a booth to view its full intelligence card",
    )
    selected_booth_id = booth_options[selected_label]

    st.divider()
    window_days = st.slider("Analysis window (days)", min_value=3, max_value=30, value=7)

    st.divider()
    page = st.radio(
        "View",
        ["📋 Booth Summary", "🏛️ Candidates", "💬 Evidence Feed", "🗺️ AC Overview"],
    )

# ── Page routing ─────────────────────────────────────────────────────────────
if page == "📋 Booth Summary":
    from dashboard.pages.booth_summary import render
    render(selected_booth_id, window_days, API_URL)

elif page == "🏛️ Candidates":
    from dashboard.pages.candidate_panel import render
    render(AC_ID, selected_booth_id, API_URL)

elif page == "💬 Evidence Feed":
    from dashboard.pages.evidence_feed import render
    render(selected_booth_id, API_URL)

elif page == "🗺️ AC Overview":
    from dashboard.pages.ac_overview import render
    render(AC_ID, booths, API_URL)
