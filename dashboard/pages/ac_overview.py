"""AC overview — table of all booths with pulse scores."""
import streamlit as st
import pandas as pd
import plotly.express as px


def render(ac_id: str, booths: list[dict], api_url: str):
    st.title(f"🗺️ AC Overview — {ac_id}")
    st.caption("All booths in the constituency with latest digital lean")

    if not booths:
        st.warning("No booth data available")
        return

    df = pd.DataFrame(booths)

    # Fill nulls
    for col in ["bjp_pulse_score", "opp_pulse_score", "digital_lean"]:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    if "digital_lean_label" not in df.columns:
        df["digital_lean_label"] = "No data"

    # ── Summary metrics ───────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Booths", len(df))
    c2.metric("Booths with Data",
              int((df.get("event_count", pd.Series([0]*len(df))) > 0).sum()))

    if "bjp_pulse_score" in df.columns:
        avg_bjp = df["bjp_pulse_score"].mean()
        avg_opp = df["opp_pulse_score"].mean() if "opp_pulse_score" in df.columns else 0
        c3.metric("Avg BJP Pulse", f"{avg_bjp:+.3f}")
        c4.metric("Avg Opp Pulse", f"{avg_opp:+.3f}")

    st.divider()

    # ── Distribution chart ────────────────────────────────────────────────────
    if "digital_lean_label" in df.columns:
        lean_counts = df["digital_lean_label"].value_counts().reset_index()
        lean_counts.columns = ["lean", "count"]
        color_map = {
            "Lean BJP": "#FF6B35",
            "Slightly BJP": "#FFA07A",
            "Contested": "#95a5a6",
            "Slightly Opp": "#87CEEB",
            "Lean Opposition": "#3498db",
            "No data": "#eeeeee",
        }
        fig = px.bar(lean_counts, x="lean", y="count",
                     color="lean", color_discrete_map=color_map,
                     title="Booth Lean Distribution")
        fig.update_layout(showlegend=False, height=250,
                          margin=dict(l=0,r=0,t=30,b=20))
        st.plotly_chart(fig, use_container_width=True)

    # ── Booth table ───────────────────────────────────────────────────────────
    display_cols = ["booth_number", "name", "total_voters",
                    "digital_lean_label", "bjp_pulse_score", "opp_pulse_score",
                    "top_issue", "confidence_label"]
    display_cols = [c for c in display_cols if c in df.columns]

    st.dataframe(
        df[display_cols].rename(columns={
            "booth_number": "#",
            "name": "Polling Station",
            "total_voters": "Voters",
            "digital_lean_label": "Digital Lean",
            "bjp_pulse_score": "BJP",
            "opp_pulse_score": "Opp",
            "top_issue": "Top Issue",
            "confidence_label": "Confidence",
        }),
        use_container_width=True,
        height=500,
    )
