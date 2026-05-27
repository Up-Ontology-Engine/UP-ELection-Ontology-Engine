"""Raw comments + news articles that generated the pulse events."""

import requests
import streamlit as st

POLARITY_EMOJI = {1: "✅ Positive", -1: "❌ Negative", 0: "➖ Neutral"}
POLARITY_COLOR = {1: "#2ecc7133", -1: "#e74c3c33", 0: "#95a5a633"}


@st.cache_data(ttl=60)
def _fetch(booth_id: str, api_url: str, source: str, limit: int):
    try:
        r = requests.get(
            f"{api_url}/booth/{booth_id}/comments",
            params={"source": source, "limit": limit},
            timeout=10,
        )
        r.raise_for_status()
        return r.json().get("comments", [])
    except Exception:
        return []


def render(booth_id: str, api_url: str):
    st.title("💬 Evidence Feed")
    st.caption("Raw pulse events that drive the booth intelligence scores")

    col1, col2, col3 = st.columns(3)
    with col1:
        source = st.selectbox("Source", ["all", "youtube", "news", "survey"])
    with col2:
        limit = st.slider("# comments", 10, 100, 25)
    with col3:
        min_conf = st.slider("Min confidence", 0.3, 0.9, 0.55)

    comments = _fetch(booth_id, api_url, source, limit)
    filtered = [c for c in comments if (c.get("confidence") or 0) >= min_conf]

    if not filtered:
        st.info("No events match these filters. Try lowering min confidence.")
        return

    st.caption(f"Showing {len(filtered)} events")

    for c in filtered:
        polarity = c.get("polarity", 0)
        entity = c.get("entity", "")
        issue = (c.get("issue") or "").replace("_", " ")
        conf = c.get("confidence", 0) or 0
        src = c.get("source", "")
        text = c.get("text_raw", "")

        bg = POLARITY_COLOR.get(polarity, "#95a5a633")
        pol_text = POLARITY_EMOJI.get(polarity, "➖")
        src_icon = "▶️" if src == "youtube" else "📰" if src == "news" else "📋"

        with st.container():
            st.markdown(
                f"""<div style="background:{bg};border-radius:8px;padding:10px 14px;margin-bottom:10px">
                <div style="font-size:0.8em;color:#555;margin-bottom:6px">
                  {pol_text} &nbsp;·&nbsp; 🏷️ {entity} {' / '+issue if issue else ''}
                  &nbsp;·&nbsp; {src_icon} {src} &nbsp;·&nbsp; conf: {conf:.2f}
                </div>
                <div style="font-size:0.95em;line-height:1.5">{text}</div>
                </div>""",
                unsafe_allow_html=True,
            )
