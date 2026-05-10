"""
Gorakhpur Political Intelligence OS
Entry point: streamlit run dashboard/app.py
"""
from __future__ import annotations
import os
import sys

# Ensure the root directory is in the sys.path so dashboard imports work regardless of CWD
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Gorakhpur Intel — Political Intelligence OS",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from dashboard.components.war_room import inject_css

inject_css()

# ── Constants ─────────────────────────────────────────────────────────────────

AC_OPTIONS = {
    "Gorakhpur Urban (GKP_322)":  "GKP_322",
    "Gorakhpur Rural (GKP_323)":  "GKP_323",
    "Caimpiyarganj (GKP_320)":    "GKP_320",
    "Pipraich (GKP_321)":         "GKP_321",
    "Sahajanwa (GKP_324)":        "GKP_324",
    "Khajani (GKP_325)":          "GKP_325",
    "Chauri-Chaura (GKP_326)":    "GKP_326",
    "Bansgaon (GKP_327)":         "GKP_327",
    "Chillupar (GKP_328)":        "GKP_328",
}

PAGES = [
    ("🏠", "Constituency Overview"),
    ("🔍", "Booth Intelligence"),
    ("🧑", "Candidate Intelligence"),
    ("🏛️", "Scheme Intelligence"),
    ("🌊", "Narrative & Sentiment"),
    ("📅", "Event Timeline"),
    ("🕸️", "Knowledge Graph"),
    ("🗺️", "Geospatial Intelligence"),
    ("🧠", "Intelligence Query"),
    ("⚠️", "Data Quality"),
    ("🚨", "Recommendations"),
]

API_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div class="wr-sidebar-brand">🗳️ Gorakhpur Intel</div>',
        unsafe_allow_html=True,
    )
    st.caption("Political Intelligence Operating System")
    st.divider()

    # AC selector
    ac_label = st.selectbox(
        "Constituency",
        options=list(AC_OPTIONS.keys()),
        index=0,
    )
    AC_ID = AC_OPTIONS[ac_label]
    AC_NAME = ac_label.split(" (")[0]

    st.divider()

    # Analysis window
    window_days = st.slider("Analysis window (days)", 3, 30, 7)

    st.divider()

    # Page navigation
    page_labels = [f"{icon} {name}" for icon, name in PAGES]
    selected_label = st.radio("Navigate", page_labels, label_visibility="collapsed")
    page_name = selected_label.split(" ", 1)[1]  # strip icon

    st.divider()
    st.caption(f"API: {API_URL}")
    st.caption("v0.1.0 — Gorakhpur KG")

# ── Load booths (needed by several pages) ─────────────────────────────────────
import requests as _req

@st.cache_data(ttl=300, show_spinner=False)
def _load_booths(ac_id: str) -> list[dict]:
    try:
        r = _req.get(f"{API_URL}/ac/{ac_id}/booths", timeout=10)
        r.raise_for_status()
        return r.json().get("booths", [])
    except Exception:
        return []

booths = _load_booths(AC_ID)

# Booth selector shown for booth-specific pages
BOOTH_PAGES = {"Booth Intelligence", "Evidence Feed"}
selected_booth_id = ""
if page_name in BOOTH_PAGES:
    if not booths:
        with st.sidebar:
            st.error("No booths loaded. Is the API running?")
    else:
        booth_opts = {
            f"Booth {b['booth_number']} — {(b.get('name') or '')[:35]}": b["booth_id"]
            for b in booths if b.get("booth_number")
        }
        with st.sidebar:
            chosen_label = st.selectbox("Booth", list(booth_opts.keys()))
            selected_booth_id = booth_opts.get(chosen_label, "")

# ── Route ─────────────────────────────────────────────────────────────────────
if page_name == "Constituency Overview":
    from dashboard.pages.ac_overview import render
    render(AC_ID, AC_NAME, booths, API_URL)

elif page_name == "Booth Intelligence":
    from dashboard.pages.booth_summary import render
    if selected_booth_id:
        render(selected_booth_id, window_days, API_URL)
    else:
        st.info("Select a booth in the sidebar.")

elif page_name == "Candidate Intelligence":
    from dashboard.pages.candidate_panel import render
    render(AC_ID, "", API_URL)

elif page_name == "Scheme Intelligence":
    from dashboard.pages.scheme_intelligence import render
    render(AC_ID, AC_NAME, API_URL)

elif page_name == "Narrative & Sentiment":
    from dashboard.pages.narrative_sentiment import render
    render(AC_ID, AC_NAME, window_days, API_URL)

elif page_name == "Event Timeline":
    from dashboard.pages.event_timeline import render
    render(AC_ID, AC_NAME, API_URL)

elif page_name == "Knowledge Graph":
    from dashboard.pages.knowledge_graph import render
    render(AC_ID, AC_NAME, API_URL)

elif page_name == "Geospatial Intelligence":
    from dashboard.pages.geo_intelligence import render
    render(AC_ID, AC_NAME, API_URL)

elif page_name == "Intelligence Query":
    from dashboard.pages.intelligence_query import render
    render(AC_ID, AC_NAME, API_URL)

elif page_name == "Data Quality":
    from dashboard.pages.data_quality import render
    render(AC_ID, AC_NAME, booths, API_URL)

elif page_name == "Recommendations":
    from dashboard.pages.recommendations import render
    render(AC_ID, AC_NAME, booths, API_URL)
