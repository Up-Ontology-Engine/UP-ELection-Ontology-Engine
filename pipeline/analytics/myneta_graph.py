"""Compatibility shim: moved into analytics.enrichment.myneta_graph."""

from __future__ import annotations

from analytics.enrichment.myneta_graph import *  # noqa: F401,F403

__all__ = [name for name in dir() if not name.startswith("_")]
"""
MyNeta Report Card — knowledge graph builder.

Reads the exported MyNeta pipeline data (``data/raw/myneta/*.json``, produced by
``ingestion.myneta_export_json``) and builds a typed knowledge graph using the
digital-democracy-pipeline graph algorithm.

The node/edge contract matches the frontend `GraphNode`/`GraphEdge`
({id, label, type, properties} / {source, target, type}) so the existing
`GraphCanvas` renderer can draw it directly.

Backend algorithm reused from DDP (`graph_builder`):
  - `_short`                  → node label truncation
  - `_build_cooccurrence_edges` → "ran against" rival edges between candidates
                                  who share a constituency+election bucket

Node types:
  Election | Constituency | Party | Candidate
  Education | Profession | CriminalRecord | AssetTier

Outputs:
  data/raw/myneta/myneta_graph.json          (canonical)
    frontend/nextjs/public/myneta_graph.json    (served statically to the frontend)

Run:
  python -m analytics.myneta_graph
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parents[1]
MYNETA_DIR = ROOT / "data" / "Myneta"
PUBLIC_OUT = ROOT / "frontend" / "nextjs" / "public" / "myneta_graph.json"


def _load_ddp_graph_builder():
    """Reuse DDP's graph algorithm helpers (``_short``, ``_build_cooccurrence_edges``).

    Prefer the installed package; fall back to loading the self-contained
    ``graph_builder.py`` by file path (the DDP package __init__ pulls in
    Python-3.11-only modules, but graph_builder itself only needs stdlib).
    """
    try:
        from digital_democracy_pipeline.graph_builder import _build_cooccurrence_edges, _short

        return _short, _build_cooccurrence_edges
    except Exception:
        import importlib.util

        gb_path = (
            ROOT
            / "digital-democracy-pipeline"
            / "src"
            / "digital_democracy_pipeline"
            / "graph_builder.py"
        )
        spec = importlib.util.spec_from_file_location("ddp_graph_builder", gb_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod._short, mod._build_cooccurrence_edges


_short, _build_cooccurrence_edges = _load_ddp_graph_builder()


# ── Asset bucketing ──────────────────────────────────────────────────────────


def _asset_tier(total_rs: int) -> tuple[str, str]:
    """Return (tier_id, human_label) for a total-asset rupee value."""
    cr = total_rs / 1e7  # crore
    if total_rs <= 0:
        return "assets_unknown", "Assets: Not Disclosed"
    if cr >= 10:
        return "assets_10cr", "₹10 Cr+"
    if cr >= 1:
        return "assets_1cr", "₹1–10 Cr"
    if total_rs >= 1e6:
        return "assets_10l", "₹10 L–1 Cr"
    return "assets_lt10l", "< ₹10 L"


def _candidate_assets(c: dict[str, Any]) -> int:
    detail = c.get("affidavit_detail") or {}
    for key in ("total_assets_detail",):
        v = detail.get(key)
        if isinstance(v, (int, float)) and v > 0:
            return int(v)
    return int((c.get("list_summary") or {}).get("total_assets") or 0)


def _profession(c: dict[str, Any]) -> str:
    detail = c.get("affidavit_detail") or {}
    prof = (detail.get("self_profession") or "").strip()
    return prof


def _norm_education(raw: str) -> str:
    e = (raw or "").strip()
    return e or "Not Stated"


# ── Graph construction ───────────────────────────────────────────────────────


def build_graph(constituency_files: list[Path]) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []
    # buckets for DDP co-occurrence: constituency+election → list of candidate ids
    rival_buckets: dict[str, set[str]] = {}

    def add_node(node_id: str, label: str, ntype: str, props: dict[str, Any] | None = None) -> str:
        if node_id not in nodes:
            nodes[node_id] = {
                "id": node_id,
                "label": _short(label, 26),
                "type": ntype,
                "properties": {"name": label, **(props or {})},
            }
        return node_id

    def add_edge(source: str, target: str, etype: str) -> None:
        edges.append({"source": source, "target": target, "type": etype})

    for path in constituency_files:
        data = json.loads(path.read_text())
        ac_id = data["ac_id"]
        ac_name = data["ac_name"]
        year = data["election_year"]

        election_id = f"election::{year}"
        const_id = f"const::{ac_id}::{year}"

        add_node(election_id, f"{year} Election", "Election", {"year": year})
        add_node(
            const_id,
            f"{ac_name} ({year})",
            "Constituency",
            {"ac_id": ac_id, "ac_name": ac_name, "year": year},
        )
        add_edge(const_id, election_id, "PART_OF")

        bucket = rival_buckets.setdefault(const_id, set())

        for c in data.get("candidates", []):
            cid = f"cand::{c['candidate_id']}"
            party = (c.get("party") or "IND").strip() or "IND"
            assets = _candidate_assets(c)
            ls = c.get("list_summary") or {}
            criminal = int(ls.get("criminal_cases") or 0)
            education = _norm_education(ls.get("education") or "")
            profession = _profession(c)
            won = (
                bool((c.get("affidavit_detail") or {}).get("is_winner"))
                or "winner" in (c.get("party_raw") or "").lower()
            )

            detail = c.get("affidavit_detail") or {}
            affidavit = {
                "movable_assets_rs": detail.get("movable_assets_rs"),
                "immovable_assets_rs": detail.get("immovable_assets_rs"),
                "total_assets_rs": detail.get("total_assets_detail") or assets,
                "liabilities": detail.get("liabilities_json") or [],
                "itr_income": detail.get("itr_income_json") or [],
                "criminal_cases_detail": detail.get("criminal_case_details_json") or [],
                "spouse_name": detail.get("spouse_name"),
                "self_profession": detail.get("self_profession"),
                "education_detail": detail.get("education_detail"),
                "voter_enrolled": detail.get("voter_enrolled_ac_name"),
                "source_url": detail.get("source_affidavit_url") or c.get("detail_url"),
            }

            add_node(
                cid,
                c["name"],
                "Candidate",
                {
                    "candidate_id": c["candidate_id"],
                    "party": party,
                    "ac_id": ac_id,
                    "ac_name": ac_name,
                    "election_year": year,
                    "assets_rs": assets,
                    "criminal_cases": criminal,
                    "education": education,
                    "profession": profession,
                    "age": ls.get("age"),
                    "liabilities_rs": ls.get("liabilities") or 0,
                    "detail_url": c.get("detail_url"),
                    "winner": won,
                    "affidavit": affidavit,
                },
            )
            bucket.add(cid)

            # Typed relationships
            add_edge(cid, const_id, "CONTESTED_IN")
            add_edge(cid, election_id, "IN_ELECTION")

            party_id = add_node(f"party::{party}", party, "Party", {"party": party})
            add_edge(cid, party_id, "REPRESENTS")

            edu_id = add_node(f"edu::{education.lower()}", education, "Education")
            add_edge(cid, edu_id, "EDUCATED")

            if profession:
                prof_id = add_node(f"prof::{profession.lower()}", profession, "Profession")
                add_edge(cid, prof_id, "WORKS_AS")

            if criminal > 0:
                crim_id = add_node("criminal::flagged", "Criminal Cases Declared", "CriminalRecord")
                add_edge(cid, crim_id, "FLAGGED")

            tier_id, tier_label = _asset_tier(assets)
            add_node(tier_id, tier_label, "AssetTier")
            add_edge(cid, tier_id, "WEALTH_TIER")

    # DDP co-occurrence: candidates who shared a constituency+election are rivals.
    rival_edges = _build_cooccurrence_edges(rival_buckets, set(nodes.keys()))
    for e in rival_edges:
        edges.append({"source": e["source"], "target": e["target"], "type": "RAN_AGAINST"})

    # Node weight = degree (DDP ranks/sizes nodes by connection count).
    degree: dict[str, int] = {nid: 0 for nid in nodes}
    for e in edges:
        if e["source"] in degree:
            degree[e["source"]] += 1
        if e["target"] in degree:
            degree[e["target"]] += 1
    for nid, n in nodes.items():
        n["properties"]["weight"] = degree[nid]

    node_list = list(nodes.values())
    type_counts: dict[str, int] = {}
    for n in node_list:
        type_counts[n["type"]] = type_counts.get(n["type"], 0) + 1

    return {
        "source": "myneta",
        "nodes": node_list,
        "edges": edges,
        "stats": {
            "total_nodes": len(node_list),
            "total_edges": len(edges),
            "node_types": type_counts,
            "constituencies": sum(1 for n in node_list if n["type"] == "Constituency"),
            "candidates": type_counts.get("Candidate", 0),
        },
    }


def run(myneta_dir: Path = MYNETA_DIR) -> dict[str, Any]:
    files = sorted(
        p
        for p in myneta_dir.glob("myneta_*.json")
        if p.name not in ("manifest.json", "myneta_graph.json")
    )
    if not files:
        raise FileNotFoundError(
            f"No MyNeta JSON found in {myneta_dir}. "
            "Run `python -m ingestion.myneta_export_json` first."
        )
    logger.info("Building MyNeta KG from %d files: %s", len(files), [f.name for f in files])
    graph = build_graph(files)

    out = myneta_dir / "myneta_graph.json"
    out.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(
        "Wrote %s (%d nodes, %d edges)",
        out,
        graph["stats"]["total_nodes"],
        graph["stats"]["total_edges"],
    )

    PUBLIC_OUT.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_OUT.write_text(json.dumps(graph, ensure_ascii=False), encoding="utf-8")
    logger.info("Wrote frontend copy → %s", PUBLIC_OUT)

    logger.info("Node types: %s", graph["stats"]["node_types"])
    return graph


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()
