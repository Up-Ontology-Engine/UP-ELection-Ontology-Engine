"""
Page 7 — Knowledge Graph Explorer
Interactive Neo4j subgraph visualization using plotly (no extra deps).
"""

from __future__ import annotations

import math
import random

import plotly.graph_objects as go
import requests
import streamlit as st

from dashboard.components.war_room import PLOTLY_LAYOUT, info_bar, inject_css, section

# Node colors by label
NODE_COLORS = {
    "Booth": "#FF6B35",
    "Issue": "#e74c3c",
    "Party": "#3498db",
    "Candidate": "#9b59b6",
    "PulseEvent": "#f39c12",
    "Narrative": "#2ecc71",
    "Scheme": "#1abc9c",
    "Panchayat": "#e67e22",
    "AssemblyConstituency": "#FF6B35",
    "AC": "#FF6B35",
    "WorkItem": "#95a5a6",
    "YouTubeVideo": "#FF0000",
    "Channel": "#cc0000",
    "default": "#8b949e",
}

NODE_SIZES = {
    "Booth": 22,
    "AssemblyConstituency": 28,
    "AC": 28,
    "Issue": 20,
    "Party": 24,
    "Candidate": 22,
    "PulseEvent": 12,
    "Narrative": 18,
    "Scheme": 18,
    "YouTubeVideo": 14,
    "Channel": 20,
    "default": 14,
}


@st.cache_data(ttl=120, show_spinner=False)
def _fetch_subgraph(entity_type: str, entity_id: str, api_url: str) -> dict:
    try:
        r = requests.get(
            f"{api_url}/graph/subgraph",
            params={"entity_type": entity_type, "entity_id": entity_id},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


def _spring_layout(
    node_ids: list[str], edges: list[tuple[str, str]], iterations: int = 60
) -> dict[str, tuple[float, float]]:
    """Pure-Python Fruchterman-Reingold layout (no networkx needed)."""
    n = len(node_ids)
    if n == 0:
        return {}
    if n == 1:
        return {node_ids[0]: (0.0, 0.0)}

    rng = random.Random(42)
    pos: dict[str, list[float]] = {
        nid: [rng.uniform(-1, 1), rng.uniform(-1, 1)] for nid in node_ids
    }

    k = math.sqrt(1.0 / n)
    t = 0.1

    node_set = set(node_ids)
    valid_edges = [(u, v) for u, v in edges if u in node_set and v in node_set]

    for _ in range(iterations):
        disp: dict[str, list[float]] = {nid: [0.0, 0.0] for nid in node_ids}

        # Repulsion
        for i, u in enumerate(node_ids):
            for j in range(i + 1, len(node_ids)):
                v = node_ids[j]
                dx = pos[u][0] - pos[v][0]
                dy = pos[u][1] - pos[v][1]
                dist = max(math.sqrt(dx * dx + dy * dy), 0.01)
                rep = k * k / dist
                disp[u][0] += dx / dist * rep
                disp[u][1] += dy / dist * rep
                disp[v][0] -= dx / dist * rep
                disp[v][1] -= dy / dist * rep

        # Attraction along edges
        for u, v in valid_edges:
            dx = pos[u][0] - pos[v][0]
            dy = pos[u][1] - pos[v][1]
            dist = max(math.sqrt(dx * dx + dy * dy), 0.01)
            attr = dist * dist / k
            disp[u][0] -= dx / dist * attr
            disp[u][1] -= dy / dist * attr
            disp[v][0] += dx / dist * attr
            disp[v][1] += dy / dist * attr

        # Apply + cool
        for nid in node_ids:
            mag = max(math.sqrt(disp[nid][0] ** 2 + disp[nid][1] ** 2), 0.01)
            pos[nid][0] += disp[nid][0] / mag * min(abs(disp[nid][0]), t)
            pos[nid][1] += disp[nid][1] / mag * min(abs(disp[nid][1]), t)
        t *= 0.97

    return {nid: (pos[nid][0], pos[nid][1]) for nid in node_ids}


def _render_graph(nodes: list[dict], edges: list[dict]) -> None:
    """Build and display a plotly network figure."""
    if not nodes:
        st.info("No graph data returned for this entity.")
        return

    node_ids = [n["id"] for n in nodes]
    edge_list = [
        (e.get("from", e.get("source", "")), e.get("to", e.get("target", ""))) for e in edges
    ]

    pos = _spring_layout(node_ids, edge_list)

    fig = go.Figure()

    # Draw edges
    for u, v in edge_list:
        if u not in pos or v not in pos:
            continue
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        fig.add_trace(
            go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                mode="lines",
                line=dict(width=1, color="#2d3a4f"),
                hoverinfo="none",
                showlegend=False,
            )
        )

    # Edge labels (relationship type)
    mid_texts: list[tuple[float, float, str]] = []
    for e, (u, v) in zip(edges, edge_list):
        if u in pos and v in pos:
            mx = (pos[u][0] + pos[v][0]) / 2
            my = (pos[u][1] + pos[v][1]) / 2
            mid_texts.append((mx, my, e.get("type", "")))

    if mid_texts:
        fig.add_trace(
            go.Scatter(
                x=[t[0] for t in mid_texts],
                y=[t[1] for t in mid_texts],
                mode="text",
                text=[t[2] for t in mid_texts],
                textfont=dict(size=8, color="#8b949e"),
                hoverinfo="none",
                showlegend=False,
            )
        )

    # Draw nodes by label group
    by_label: dict[str, list[dict]] = {}
    for n in nodes:
        lbl = n.get("label", "default")
        by_label.setdefault(lbl, []).append(n)

    for label, group in by_label.items():
        xs = [pos[n["id"]][0] for n in group if n["id"] in pos]
        ys = [pos[n["id"]][1] for n in group if n["id"] in pos]
        texts = [n.get("display_name") or n["id"] for n in group if n["id"] in pos]
        color = NODE_COLORS.get(label, NODE_COLORS["default"])
        size = NODE_SIZES.get(label, NODE_SIZES["default"])
        tips = [n.get("tooltip", n.get("display_name", n["id"])) for n in group if n["id"] in pos]

        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="markers+text",
                name=label,
                marker=dict(size=size, color=color, line=dict(color="#0a0e1a", width=2)),
                text=texts,
                textposition="bottom center",
                textfont=dict(size=9, color="#e6edf3"),
                hovertext=tips,
                hoverinfo="text",
            )
        )

    fig.update_layout(
        **{
            **PLOTLY_LAYOUT,
            "height": 560,
            "xaxis": dict(showgrid=False, zeroline=False, showticklabels=False),
            "yaxis": dict(showgrid=False, zeroline=False, showticklabels=False),
            "margin": dict(l=0, r=0, t=30, b=0),
            "legend": dict(
                orientation="h",
                yanchor="bottom",
                y=1.01,
                xanchor="left",
                x=0,
                font=dict(size=10),
            ),
        },
    )
    st.plotly_chart(fig, use_container_width=True)


def render(ac_id: str, ac_name: str, api_url: str) -> None:
    inject_css()

    st.markdown("## 🕸️ Knowledge Graph Explorer")
    info_bar(f"AC: {ac_name}  |  Navigate entity relationships in the Neo4j knowledge graph")

    col1, col2 = st.columns([1, 2])
    with col1:
        entity_type = st.selectbox(
            "Focus entity",
            ["AC", "Booth", "Issue", "Candidate", "Party", "Scheme", "YouTubeVideo", "Channel"],
        )
    with col2:
        entity_id = st.text_input(
            "Entity ID",
            value=ac_id if entity_type == "AC" else "",
            placeholder=f"e.g. {ac_id}",
            help="Enter the exact ID of the entity to explore (e.g. GKP_322, water, BJP)",
        )

    col3, col4 = st.columns([1, 3])
    with col3:
        hops = st.selectbox("Graph depth (hops)", [1, 2], index=0)
    with col4:
        st.markdown("")
        explore = st.button("🔍 Explore Graph", type="primary", use_container_width=True)

    if explore and entity_id:
        with st.spinner("Querying Neo4j knowledge graph…"):
            data = _fetch_subgraph(entity_type, entity_id.strip(), api_url)

        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        if not nodes:
            st.warning("Neo4j returned no results. Is the graph loaded?")
            st.code("Run: python -m flows.graph.flow_load_graph --stage neo4j")
            _show_legend()
            _render_demo_graph(ac_id)
            return

        c_nodes, c_edges = st.columns(2)
        c_nodes.metric("Nodes", len(nodes))
        c_edges.metric("Relationships", len(edges))

        _render_graph(nodes, edges)
        _show_legend()
        _render_node_table(nodes)

    elif not explore:
        _show_legend()
        st.divider()
        st.markdown("### Try an example")
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            if st.button("🗳️ Constituency", use_container_width=True):
                st.session_state["kg_type"] = "AC"
                st.session_state["kg_id"] = ac_id
        with col_b:
            if st.button("💧 Water Network", use_container_width=True):
                st.session_state["kg_type"] = "Issue"
                st.session_state["kg_id"] = "water"
        with col_c:
            if st.button("🎯 BJP Network", use_container_width=True):
                st.session_state["kg_type"] = "Party"
                st.session_state["kg_id"] = "BJP"
        with col_d:
            if st.button("▶️ YouTube Channel", use_container_width=True):
                st.session_state["kg_type"] = "Channel"
                st.session_state["kg_id"] = "@ABPGanga"

        # If a quick-explore was clicked
        if "kg_id" in st.session_state:
            with st.spinner("Querying Neo4j…"):
                data = _fetch_subgraph(
                    st.session_state.pop("kg_type", "AC"),
                    st.session_state.pop("kg_id", ac_id),
                    api_url,
                )
            nodes = data.get("nodes", [])
            edges = data.get("edges", [])
            if nodes:
                _render_graph(nodes, edges)
            else:
                _render_demo_graph(ac_id)

        else:
            _render_demo_graph(ac_id)


def _show_legend() -> None:
    section("Node Legend", "🎨")
    cols = st.columns(len(NODE_COLORS) - 1)
    for i, (label, color) in enumerate(NODE_COLORS.items()):
        if label == "default":
            continue
        with cols[i % len(cols)]:
            st.markdown(
                f'<span style="background:{color};border-radius:50%;display:inline-block;'
                f'width:12px;height:12px;margin-right:4px"></span>'
                f'<span style="font-size:.82em">{label}</span>',
                unsafe_allow_html=True,
            )


def _render_node_table(nodes: list[dict]) -> None:
    section("Node Details", "📋")
    import pandas as pd

    rows = [
        {
            "Label": n.get("label", "?"),
            "ID": n.get("id", "?"),
            "Name": n.get("display_name") or n.get("id", "?"),
            "Info": n.get("tooltip", ""),
        }
        for n in nodes[:50]
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, height=250)


def _render_demo_graph(ac_id: str) -> None:
    """Static demo graph so the page looks functional before Neo4j is loaded."""
    st.divider()
    st.caption("📋 Demo graph — load Neo4j data to see live relationships")

    demo_nodes = [
        {
            "id": ac_id,
            "label": "AssemblyConstituency",
            "display_name": "GKP Urban",
            "tooltip": "Gorakhpur Urban AC",
        },
        {"id": "BJP", "label": "Party", "display_name": "BJP", "tooltip": "Bharatiya Janata Party"},
        {"id": "SP", "label": "Party", "display_name": "SP", "tooltip": "Samajwadi Party"},
        {"id": "water", "label": "Issue", "display_name": "Water", "tooltip": "Water supply issue"},
        {"id": "jobs", "label": "Issue", "display_name": "Jobs", "tooltip": "Employment issue"},
        {
            "id": "roads",
            "label": "Issue",
            "display_name": "Roads",
            "tooltip": "Roads & connectivity",
        },
        {
            "id": "YOGI_2022",
            "label": "Candidate",
            "display_name": "Yogi (BJP)",
            "tooltip": "Yogi Adityanath",
        },
        {"id": "b_223", "label": "Booth", "display_name": "Booth 223", "tooltip": "Rustampur area"},
        {
            "id": "b_185",
            "label": "Booth",
            "display_name": "Booth 185",
            "tooltip": "Civil Lines area",
        },
        {"id": "jjm", "label": "Scheme", "display_name": "JJM", "tooltip": "Jal Jeevan Mission"},
        {
            "id": "abpganga",
            "label": "Channel",
            "display_name": "ABP Ganga",
            "tooltip": "ABP Ganga YouTube channel",
        },
        {
            "id": "yt_gkp1",
            "label": "YouTubeVideo",
            "display_name": "GKP Election",
            "tooltip": "Gorakhpur chunav coverage",
        },
        {
            "id": "yt_gkp2",
            "label": "YouTubeVideo",
            "display_name": "Yogi Rally",
            "tooltip": "Yogi Adityanath rally coverage",
        },
    ]
    demo_edges = [
        {"from": ac_id, "to": "b_223", "type": "HAS_BOOTH"},
        {"from": ac_id, "to": "b_185", "type": "HAS_BOOTH"},
        {"from": "YOGI_2022", "to": ac_id, "type": "CONTESTED_IN"},
        {"from": "YOGI_2022", "to": "BJP", "type": "REPRESENTS"},
        {"from": "b_223", "to": "water", "type": "TOP_ISSUE"},
        {"from": "b_223", "to": "jobs", "type": "TOP_ISSUE"},
        {"from": "b_185", "to": "roads", "type": "TOP_ISSUE"},
        {"from": "jjm", "to": "water", "type": "ADDRESSES"},
        {"from": "yt_gkp1", "to": ac_id, "type": "ABOUT_AC"},
        {"from": "yt_gkp1", "to": "abpganga", "type": "FROM_CHANNEL"},
        {"from": "yt_gkp2", "to": "abpganga", "type": "FROM_CHANNEL"},
        {"from": "yt_gkp2", "to": "jobs", "type": "MENTIONS_ISSUE"},
    ]
    _render_graph(demo_nodes, demo_edges)
