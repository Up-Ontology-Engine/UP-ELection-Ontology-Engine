"""
Page: Political Intelligence Query
Natural language → Groq Cypher generation → Neo4j results.
"""
from __future__ import annotations
import requests
import streamlit as st
import pandas as pd

from dashboard.components.war_room import inject_css, section, info_bar

EXAMPLES = [
    "Show all candidates with criminal cases",
    "Which party has the most candidates in Gorakhpur Urban?",
    "Find booths where water is the top issue",
    "Show candidates ordered by net worth in crores",
    "Which YouTube channels have the most videos about Gorakhpur?",
    "List all issues linked to Gorakhpur Urban constituency",
    "Show BJP candidates and their criminal record counts",
    "Find all panchayats in Gorakhpur Rural AC",
    "Which booth has the most YouTube videos mentioning it?",
    "Show candidates who contested in 2022 with their party",
    "Find schemes related to water in the knowledge graph",
    "Show dynastic candidates — find candidates sharing the same family name",
]


def render(ac_id: str, ac_name: str, api_url: str) -> None:
    inject_css()
    st.markdown("## 🧠 Political Intelligence Query")
    info_bar(
        f"AC: {ac_name}  |  "
        "Ask any question in English — AI generates Cypher, Neo4j answers in real time"
    )

    st.markdown(
        """
        <div style="background:#1a2233;border-left:3px solid #FF6B35;padding:10px 16px;
                    border-radius:4px;margin-bottom:12px;font-size:.88em;color:#8b949e">
        Powered by <b>Groq LLM</b> + <b>Neo4j Knowledge Graph</b>.
        The AI understands your political question, writes a graph query, and executes it.
        Results are live from the knowledge graph.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Quick-select examples
    section("Example Queries", "💡")
    cols = st.columns(3)
    clicked = None
    for i, eq in enumerate(EXAMPLES):
        with cols[i % 3]:
            if st.button(eq, key=f"ex_{i}", use_container_width=True):
                clicked = eq

    st.divider()

    # Question input
    init_val = clicked or st.session_state.get("iq_q", "")
    question = st.text_area(
        "Your question",
        value=init_val,
        height=80,
        placeholder=(
            "e.g. Show candidates with more than 2 criminal cases "
            "ordered by total assets"
        ),
        key="iq_input",
    )

    c_run, c_clr, _ = st.columns([1, 1, 5])
    run_btn   = c_run.button("Run Query", type="primary", use_container_width=True)
    clear_btn = c_clr.button("Clear",                   use_container_width=True)

    if clear_btn:
        st.session_state.pop("iq_q", None)
        st.rerun()

    if run_btn and question.strip():
        st.session_state["iq_q"] = question.strip()
        _execute_and_display(question.strip(), api_url)
    elif run_btn:
        st.warning("Please enter a question.")
    elif "iq_q" in st.session_state and not run_btn:
        # Re-show last result on page re-render
        _execute_and_display(st.session_state["iq_q"], api_url)


def _execute_and_display(question: str, api_url: str) -> None:
    with st.spinner("Generating Cypher and querying Neo4j…"):
        try:
            resp = requests.post(
                f"{api_url}/reasoning/query",
                json={"question": question},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            st.error(f"Request failed: {exc}")
            return

    # Generated Cypher (collapsed by default)
    cypher = data.get("cypher")
    if cypher:
        with st.expander("Generated Cypher", expanded=False):
            st.code(cypher, language="cypher")

    # Error display
    if data.get("error"):
        st.error(data["error"])
        return

    # Results
    results  = data.get("results", [])
    row_count = data.get("row_count", len(results))

    section(f"Results — {row_count} row{'s' if row_count != 1 else ''}", "📊")

    if not results:
        st.info("Query returned no results. The data may not be loaded yet or try rephrasing.")
        return

    try:
        df = pd.DataFrame(results)
        # Tidy column names
        df.columns = [str(c).replace("_", " ").title() for c in df.columns]
        st.dataframe(df, use_container_width=True, height=min(60 + len(df) * 35, 500))
    except Exception:
        for row in results[:30]:
            st.json(row)
