"""
caste_analysis.py — Streamlit dashboard page
==============================================
Visualises the Surname-Caste Electoral Influence analysis results.

Panels
------
1. Constituency selector + metadata bar
2. Surname Frequency (top-20 bar chart)
3. Caste–Party Correlation Heatmap (Pearson r)
4. Booth-Level Scatter (caste share vs party vote share)
5. Influence Score Table (ranked)
6. Candidate Caste Tag (winner analysis)
7. Linkage Quality Report
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
TRANSFORMED = ROOT / "data" / "transformed"
SEEDS = ROOT / "data" / "seeds"

# ── Color palette ──────────────────────────────────────────────────────────────
PARTY_COLORS = {
    "BJP": "#FF6B35",
    "SP": "#E63946",
    "BSP": "#2196F3",
    "INC": "#4CAF50",
    "IND": "#9E9E9E",
    "NOTA": "#607D8B",
}

CATEGORY_COLORS = {
    "OBC": "#FF9800",
    "OBC_Baniya": "#FFB74D",
    "SC": "#9C27B0",
    "General": "#2196F3",
    "Muslim": "#4CAF50",
    "General_Ambiguous": "#78909C",
    "Ambiguous": "#BDBDBD",
    "Unknown": "#EEEEEE",
}

_CSS = """
<style>
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #0f3460;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 4px 0;
    }
    .metric-card h4 { color: #e0e0e0; font-size: 12px; margin: 0; font-weight: 400; }
    .metric-card h2 { color: #ffffff; font-size: 22px; margin: 4px 0 0; font-weight: 700; }
    .metric-card .sub { color: #90CAF9; font-size: 11px; }
    .influence-high  { color: #ef5350; font-weight: 700; }
    .influence-mid   { color: #FFA726; font-weight: 600; }
    .influence-low   { color: #66BB6A; font-weight: 500; }
    .swing-high { color: #ef5350; }
    .swing-med  { color: #FFA726; }
    .swing-low  { color: #66BB6A; }
</style>
"""


# ── Loaders ────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def get_voter_roll_caste() -> pd.DataFrame | None:
    p = TRANSFORMED / "voter_roll_normalised_caste.parquet"
    if not p.exists():
        return None
    return pd.read_parquet(p)


@st.cache_data(ttl=300)
def get_analysis() -> pd.DataFrame | None:
    p = TRANSFORMED / "caste_booth_analysis.parquet"
    if not p.exists():
        return None
    return pd.read_parquet(p)


@st.cache_data(ttl=300)
def get_influence_scores() -> dict:
    p = TRANSFORMED / "caste_influence_scores.json"
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


@st.cache_data(ttl=300)
def get_linkage() -> pd.DataFrame | None:
    p = TRANSFORMED / "booth_linkage_map.json"
    if not p.exists():
        return None
    return pd.read_json(p)


@st.cache_data(ttl=300)
def get_candidates() -> pd.DataFrame | None:
    p = TRANSFORMED / "candidates_normalized.parquet"
    if not p.exists():
        return None
    return pd.read_parquet(p)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _party_color(party: str) -> str:
    return PARTY_COLORS.get(party.upper(), "#78909C")


def _category_color(cat: str) -> str:
    return CATEGORY_COLORS.get(cat, "#BDBDBD")


def _not_available(label: str = "Data not yet generated") -> None:
    st.info(
        f"⚠️ **{label}**\n\n"
        "Run the pipeline first:\n"
        "```bash\npython -m analytics.surname_caste.run_pipeline --ac 322\n```",
        icon="🔄",
    )


# ── Main page ──────────────────────────────────────────────────────────────────

def render() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    st.markdown("## 🗳️ Caste & Surname Electoral Influence Analysis")
    st.markdown(
        "Correlates voter surname distribution with booth-level election outcomes "
        "to surface which caste groups have the strongest electoral influence."
    )
    
    # ── AI Summary ─────────────────────────────────────────────────────────
    @st.cache_data(ttl=3600)
    def generate_ai_summary(table_data: list[dict]) -> str:
        import os
        from groq import Groq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return "GROQ_API_KEY not found in environment."
        
        try:
            client = Groq(api_key=api_key)
            prompt = f"Here is data on the most influential caste groups in an election:\n{json.dumps(table_data[:10], indent=2)}\nSummarize the key takeaways in 3 simple bullet points. Keep it short and easy to understand for a political strategist."
            res = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return res.choices[0].message.content
        except Exception as e:
            return f"Failed to generate summary: {e}"

    st.divider()

    # ── Sidebar controls ────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ Controls")
        ac_options = {
            "322 — Gorakhpur City": 322,
            "320 — Caimpiyarganj": 320,
            "321 — Pipraich": 321,
            "323 — Gorakhpur Urban": 323,
        }
        selected_ac_label = st.selectbox("Assembly Constituency", list(ac_options.keys()))
        selected_ac = ac_options[selected_ac_label]

        min_pop_share = st.slider("Min. population share for heatmap (%)", 0, 10, 2) / 100
        dominance_threshold = st.slider("Caste dominance threshold (%)", 10, 50, 25) / 100

        category_filter = st.multiselect(
            "Social categories",
            ["OBC", "OBC_Baniya", "SC", "General", "Muslim", "Ambiguous", "Unknown"],
            default=["OBC", "OBC_Baniya", "SC", "General", "Muslim"],
        )

        include_unknown = st.checkbox("Include Unknown caste in surname chart", value=False)

    ac_key = f"ac_{selected_ac}"

    # ── Load data ───────────────────────────────────────────────────────────
    vr_df = get_voter_roll_caste()
    analysis_df = get_analysis()
    scores = get_influence_scores()
    linkage_df = get_linkage()
    candidates_df = get_candidates()

    data_ready = vr_df is not None and analysis_df is not None and bool(scores)

    # ── Metadata bar ────────────────────────────────────────────────────────
    if vr_df is not None:
        total_voters = len(vr_df[vr_df["ac_number"] == selected_ac]) if "ac_number" in vr_df.columns else len(vr_df)
        n_parts = vr_df["part_number"].nunique() if "part_number" in vr_df.columns else 0
        n_unique_surnames = vr_df["surname"].nunique() if "surname" in vr_df.columns else 0
    else:
        total_voters = n_parts = n_unique_surnames = 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("📋 Total Voters", f"{total_voters:,}")
    with c2:
        st.metric("🗂️ Voter Roll Parts", n_parts)
    with c3:
        st.metric("🔤 Unique Surnames", n_unique_surnames)
    with c4:
        if analysis_df is not None:
            st.metric("🏠 Booths Analysed", len(analysis_df))
        else:
            st.metric("🏠 Booths Analysed", "—")

    st.divider()

    # ── Panel 1: Surname Frequency ──────────────────────────────────────────
    st.markdown("### 📊 Panel 1 — Top Surnames in Voter Roll")
    if vr_df is not None and "surname" in vr_df.columns:
        surname_df = vr_df.copy()
        if not include_unknown:
            surname_df = surname_df[surname_df["surname"] != "UNKNOWN"]

        top_surnames = (
            surname_df["surname"]
            .value_counts()
            .reset_index()
            .rename(columns={"surname": "Surname", "count": "Count"})
            .head(25)
        )

        # Merge with caste info
        if "caste_group" in surname_df.columns:
            caste_for_surname = (
                surname_df.groupby("surname")["social_category"]
                .agg(lambda x: x.mode()[0] if len(x) > 0 else "Unknown")
                .reset_index()
                .rename(columns={"surname": "Surname", "social_category": "Category"})
            )
            top_surnames = top_surnames.merge(caste_for_surname, on="Surname", how="left")
            top_surnames["Category"] = top_surnames["Category"].fillna("Unknown")
            color_col = "Category"
            color_map = CATEGORY_COLORS
        else:
            top_surnames["Category"] = "Unknown"
            color_col = "Category"
            color_map = {"Unknown": "#78909C"}

        fig = px.bar(
            top_surnames,
            x="Count",
            y="Surname",
            orientation="h",
            color=color_col,
            color_discrete_map=color_map,
            title="Top 25 Surnames by Frequency",
            labels={"Count": "Voter Count", "Surname": ""},
            height=550,
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
            yaxis={"categoryorder": "total ascending"},
            legend_title="Social Category",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        _not_available("Voter roll with caste data not found")

    # ── Panel 2: Caste–Party Correlation Heatmap ────────────────────────────
    st.markdown("### 🌡️ Panel 2 — Caste × Party Correlation Heatmap (Pearson r)")
    st.caption("How strongly does each caste group's population share correlate with each party's vote share across booths?")

    if data_ready and ac_key in scores:
        ac_scores = scores[ac_key]

        # Filter by category and min pop share
        filtered_castes = {
            caste: info for caste, info in ac_scores.items()
            if info.get("population_share", 0) >= min_pop_share
            and (info.get("social_category") in category_filter if "social_category" in info else True)
        }

        # Build matrix
        party_keys = sorted({
            k.replace("pearson_r_", "")
            for caste_info in ac_scores.values()
            for k in caste_info.keys()
            if k.startswith("pearson_r_")
        })
        caste_list = list(filtered_castes.keys())

        if caste_list and party_keys:
            matrix = pd.DataFrame(index=caste_list, columns=party_keys, dtype=float)
            for caste in caste_list:
                for party in party_keys:
                    val = filtered_castes[caste].get(f"pearson_r_{party}")
                    matrix.loc[caste, party] = float(val) if val is not None else None

            # Drop parties with all NaN
            matrix = matrix.dropna(axis=1, how="all")

            fig_hm = px.imshow(
                matrix.astype(float),
                color_continuous_scale="RdBu_r",
                zmin=-1, zmax=1,
                text_auto=".2f",
                aspect="auto",
                title="Pearson Correlation: Caste Share vs Party Vote Share",
                labels={"color": "Pearson r"},
                height=max(400, len(caste_list) * 28),
            )
            fig_hm.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#e0e0e0",
                xaxis_title="Party",
                yaxis_title="Caste Group",
            )
            st.plotly_chart(fig_hm, use_container_width=True)
        else:
            st.info("Not enough caste groups pass the filter — lower the min population share.")
    else:
        _not_available("Influence scores not found")

    # ── Panel 3: Booth Scatter ───────────────────────────────────────────────
    st.markdown("### 🔵 Panel 3 — Booth-Level Scatter: Caste Share vs Party Vote Share")

    if analysis_df is not None:
        caste_cols = [c for c in analysis_df.columns if c.startswith("caste_share_")]
        party_cols = [c for c in analysis_df.columns if c.startswith("party_share_")]

        if caste_cols and party_cols:
            col_sel1, col_sel2 = st.columns(2)
            with col_sel1:
                selected_caste_col = st.selectbox(
                    "Select caste group (X axis)",
                    caste_cols,
                    format_func=lambda c: c.replace("caste_share_", ""),
                    key="scatter_caste",
                )
            with col_sel2:
                selected_party_col = st.selectbox(
                    "Select party (Y axis)",
                    party_cols,
                    format_func=lambda c: c.replace("party_share_", ""),
                    key="scatter_party",
                )

            scatter_df = analysis_df[
                [selected_caste_col, selected_party_col, "winner_party",
                 "part_number", "voter_roll_count", "match_status"]
            ].dropna(subset=[selected_caste_col, selected_party_col])

            scatter_df["caste_label"] = selected_caste_col.replace("caste_share_", "")
            scatter_df["party_label"] = selected_party_col.replace("party_share_", "")

            fig_sc = px.scatter(
                scatter_df,
                x=selected_caste_col,
                y=selected_party_col,
                color="winner_party",
                color_discrete_map=PARTY_COLORS,
                size="voter_roll_count",
                size_max=20,
                hover_data=["part_number", "match_status", "voter_roll_count"],
                trendline="ols",
                labels={
                    selected_caste_col: f"{selected_caste_col.replace('caste_share_','').title()} Share",
                    selected_party_col: f"{selected_party_col.replace('party_share_','').title()} Vote Share",
                    "winner_party": "Winner",
                },
                title=f"{selected_caste_col.replace('caste_share_', '')} presence vs "
                      f"{selected_party_col.replace('party_share_', '')} vote share",
                height=480,
            )
            fig_sc.update_layout(
                plot_bgcolor="rgba(14,17,23,0.9)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#e0e0e0",
            )
            st.plotly_chart(fig_sc, use_container_width=True)
        else:
            _not_available("Analysis data incomplete — missing caste/party share columns")
    else:
        _not_available("Caste booth analysis not found")

    # ── Panel 4: Influence Score Table ──────────────────────────────────────
    st.markdown("### 🏆 Panel 4 — Caste Group Influence Score Table")

    if data_ready and ac_key in scores:
        from analytics.surname_caste.influence_scorer import top_influential_castes

        all_castes_rows = top_influential_castes(scores, ac_key=ac_key, n=50)

        table_data = []
        for row in all_castes_rows:
            table_data.append(
                {
                    "Caste Group": row["caste"],
                    "Pop. Share %": f"{row.get('population_share', 0):.1%}",
                    "Dominant Party": row.get("dominant_party") or "—",
                    "Win% (Dom Booths)": f"{row['dominant_party_win_pct']:.0%}" if row.get("dominant_party_win_pct") else "—",
                    "Swing Potential": row.get("swing_potential") or "—",
                    "Best Corr Party": row.get("best_corr_party") or "—",
                    "Best Corr r": f"{row['best_corr_r']:.3f}" if row.get("best_corr_r") else "—",
                    "Dominant Booths": row.get("n_booths_dominant") or 0,
                    "Candidate Match": "✅" if row.get("candidate_caste_match") else "❌",
                }
            )

        st.dataframe(
            pd.DataFrame(table_data),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Swing Potential": st.column_config.TextColumn(
                    "Swing Potential",
                    help="HIGH = caste is not locked to one party",
                ),
                "Candidate Match": st.column_config.TextColumn(
                    "Winner Match",
                    help="Does the election winner's surname belong to this caste?",
                ),
            },
        )
        
        st.info("🤖 **AI Summary**\n\n" + generate_ai_summary(table_data))
    else:
        _not_available("Influence scores not found")

    # ── Panel 5: Candidate Caste Tag ────────────────────────────────────────
    st.markdown("### 🎖️ Panel 5 — Candidate Caste Analysis")

    if candidates_df is not None:
        cand_ac = candidates_df[candidates_df["constituency_no"] == str(selected_ac)].copy()
        if not cand_ac.empty:
            years = sorted(cand_ac["year"].dropna().unique(), reverse=True)
            sel_year = st.selectbox("Election Year", years, key="cand_year")
            cand_year = cand_ac[cand_ac["year"] == sel_year].sort_values("position")

            # Load caste for each candidate
            try:
                from analytics.surname_caste.caste_mapper import CasteMapper
                mapper = CasteMapper(use_llm=False)
                cand_year["caste_group"] = cand_year["candidate_surname"].apply(
                    mapper.lookup_field("caste_group")
                )
                cand_year["social_category"] = cand_year["candidate_surname"].apply(
                    mapper.lookup_field("social_category")
                )
            except Exception:
                cand_year["caste_group"] = "Unknown"
                cand_year["social_category"] = "Unknown"

            display_cols = [
                "position", "candidate_name", "candidate_surname",
                "caste_group", "social_category", "party",
                "votes", "vote_share_pct", "winner",
            ]
            available = [c for c in display_cols if c in cand_year.columns]
            st.dataframe(
                cand_year[available].rename(columns={
                    "position": "Rank",
                    "candidate_name": "Candidate",
                    "candidate_surname": "Surname",
                    "caste_group": "Caste",
                    "social_category": "Category",
                    "party": "Party",
                    "votes": "Votes",
                    "vote_share_pct": "Vote Share %",
                    "winner": "Winner",
                }),
                use_container_width=True,
                hide_index=True,
            )

            # Visual breakdown
            if "caste_group" in cand_year.columns:
                fig_cd = px.bar(
                    cand_year[cand_year["votes"].notna()].sort_values("votes", ascending=False),
                    x="candidate_name",
                    y="votes",
                    color="caste_group",
                    text="vote_share_pct",
                    labels={
                        "candidate_name": "Candidate",
                        "votes": "Votes",
                        "caste_group": "Caste Group",
                    },
                    title=f"AC {selected_ac} — {sel_year} Candidate Votes by Caste Group",
                    height=380,
                )
                fig_cd.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
                fig_cd.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#e0e0e0",
                    xaxis_tickangle=-30,
                )
                st.plotly_chart(fig_cd, use_container_width=True)
        else:
            st.info(f"No candidate data found for AC {selected_ac}")
    else:
        _not_available("Candidates data not found")

    # ── Panel 6: Linkage Quality ─────────────────────────────────────────────
    st.markdown("### 🔗 Panel 6 — Booth Linkage Quality Report")

    if linkage_df is not None:
        status_counts = linkage_df["match_status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]

        col_lq1, col_lq2 = st.columns([1, 2])
        with col_lq1:
            fig_pie = px.pie(
                status_counts,
                names="Status",
                values="Count",
                color="Status",
                color_discrete_map={
                    "MATCHED": "#4CAF50",
                    "SUSPECT": "#FF9800",
                    "MISMATCH": "#f44336",
                    "NO_FORM20": "#9E9E9E",
                    "NO_VOTER_ROLL": "#607D8B",
                },
                title="Linkage Status Distribution",
                hole=0.4,
            )
            fig_pie.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#e0e0e0",
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_lq2:
            # Delta distribution for matched booths
            matched = linkage_df[linkage_df["match_status"].isin(["MATCHED", "SUSPECT"])].copy()
            if len(matched) > 0 and "delta_pct" in matched.columns:
                fig_hist = px.histogram(
                    matched,
                    x="delta_pct",
                    color="match_status",
                    color_discrete_map={"MATCHED": "#4CAF50", "SUSPECT": "#FF9800"},
                    nbins=20,
                    title="Voter Count Delta Distribution (matched booths)",
                    labels={"delta_pct": "Delta % (voter roll vs Form20 electors)"},
                    height=300,
                )
                fig_hist.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#e0e0e0",
                )
                st.plotly_chart(fig_hist, use_container_width=True)

        with st.expander("View Full Linkage Table"):
            st.dataframe(
                linkage_df.sort_values("part_number"),
                use_container_width=True,
                hide_index=True,
            )
    else:
        _not_available("Linkage map not found")

    # ── Footer ───────────────────────────────────────────────────────────────
    st.divider()
    st.caption(
        "**Data**: Voter Roll 2026 (Electoral Commission of India) × Form 20 2022 (Vidhan Sabha results). "
        "Caste inference via surname → caste mapping (Groq LLM + bootstrap dictionary). "
        "Correlation analysis uses Pearson r across booth-level aggregate data. "
        "**Note**: Caste classifications are probabilistic — single-word or ambiguous names may be misclassified."
    )


# Allow running as standalone page
if __name__ == "__main__":
    st.set_page_config(
        page_title="Caste Influence Analysis | Gorakhpur KG",
        page_icon="🗳️",
        layout="wide",
    )
    render()
