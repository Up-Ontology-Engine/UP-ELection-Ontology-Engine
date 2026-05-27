"""
Neo4j GDS Booth Influence Scoring — PageRank + Louvain Community Detection.

This module wraps Neo4j Graph Data Science (GDS) library calls to:
  1. Project a named in-memory graph (booth + AC + issue nodes + relationships).
  2. Run PageRank to score booth influence based on graph connectivity.
  3. Run Louvain community detection to group booths with shared issue dynamics.
  4. Write the scores back onto Booth nodes (influence_score, community_id).

Prerequisites:
  - Neo4j GDS plugin installed in the Neo4j server (neo4j-graph-data-science-*.jar)
  - GDS 2.x compatible version: https://neo4j.com/product/graph-data-science/

Usage:
    python -m graph.analytics.gds_booth_influence
    # or import and call from other modules:
    from graph.analytics.gds_booth_influence import run_influence_analysis
    run_influence_analysis()

Environment:
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD must be set.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ── constants ────────────────────────────────────────────────────────────────

# Named graph projection for the GDS in-memory catalogue
_GRAPH_NAME = "booth_influence_graph"

# Node labels and relationship types to include in the projection
_NODE_LABELS = ["Booth", "AssemblyConstituency", "Issue", "Party", "Candidate"]
_REL_TYPES = ["HAS_BOOTH", "MENTIONS_ISSUE", "REPRESENTS", "CONTESTED_IN", "HAS_NARRATIVE"]

# PageRank configuration
_PAGERANK_CONFIG = {
    "maxIterations": 20,
    "dampingFactor": 0.85,
    "tolerance": 1.0e-7,
    "writeProperty": "influence_score",  # written back to Booth nodes
}

# Louvain configuration
_LOUVAIN_CONFIG = {
    "maxIterations": 10,
    "tolerance": 0.0001,
    "includeIntermediateCommunities": False,
    "writeProperty": "community_id",  # written back to Booth nodes
}


# ── GDS wrapper functions ────────────────────────────────────────────────────


def _drop_graph_if_exists(session) -> None:
    """Drop the named graph projection if it already exists in the GDS catalogue."""
    try:
        result = session.run(
            "CALL gds.graph.exists($name) YIELD exists",
            name=_GRAPH_NAME,
        ).single()
        if result and result["exists"]:
            session.run("CALL gds.graph.drop($name)", name=_GRAPH_NAME)
            logger.info("[gds] Dropped existing graph projection '%s'.", _GRAPH_NAME)
    except Exception as exc:
        logger.warning("[gds] Could not check/drop graph projection: %s", exc)


def _project_graph(session) -> dict:
    """
    Create a native GDS graph projection over Booth-centric subgraph.

    Returns the GDS project result dict, or raises on failure.
    """
    result = session.run(
        """
        CALL gds.graph.project(
            $name,
            $node_labels,
            {
                HAS_BOOTH:      {orientation: 'UNDIRECTED'},
                MENTIONS_ISSUE: {orientation: 'UNDIRECTED'},
                REPRESENTS:     {orientation: 'UNDIRECTED'},
                CONTESTED_IN:   {orientation: 'UNDIRECTED'},
                HAS_NARRATIVE:  {orientation: 'UNDIRECTED'}
            }
        )
        YIELD graphName, nodeCount, relationshipCount
        """,
        name=_GRAPH_NAME,
        node_labels=_NODE_LABELS,
    ).single()
    if not result:
        raise RuntimeError("gds.graph.project returned no result.")
    logger.info(
        "[gds] Graph projected: %s nodes=%d, rels=%d",
        result["graphName"],
        result["nodeCount"],
        result["relationshipCount"],
    )
    return dict(result)


def _run_pagerank(session) -> dict:
    """
    Run PageRank on the projected graph and write scores back to Booth nodes.
    Returns stats dict (nodePropertiesWritten, ranIterations, etc.).
    """
    result = session.run(
        """
        CALL gds.pageRank.write($name, {
            maxIterations:   $maxIterations,
            dampingFactor:   $dampingFactor,
            tolerance:       $tolerance,
            writeProperty:   $writeProperty
        })
        YIELD nodePropertiesWritten, ranIterations, didConverge,
              centralityDistribution
        """,
        name=_GRAPH_NAME,
        **_PAGERANK_CONFIG,
    ).single()
    if not result:
        raise RuntimeError("gds.pageRank.write returned no result.")
    logger.info(
        "[gds] PageRank done: wrote=%d  iters=%d  converged=%s",
        result["nodePropertiesWritten"],
        result["ranIterations"],
        result["didConverge"],
    )
    return dict(result)


def _run_louvain(session) -> dict:
    """
    Run Louvain community detection and write community IDs back to Booth nodes.
    Returns stats dict.
    """
    result = session.run(
        """
        CALL gds.louvain.write($name, {
            maxIterations:                  $maxIterations,
            tolerance:                      $tolerance,
            includeIntermediateCommunities: $includeIntermediateCommunities,
            writeProperty:                  $writeProperty
        })
        YIELD communityCount, modularity, nodePropertiesWritten
        """,
        name=_GRAPH_NAME,
        **_LOUVAIN_CONFIG,
    ).single()
    if not result:
        raise RuntimeError("gds.louvain.write returned no result.")
    logger.info(
        "[gds] Louvain done: communities=%d  modularity=%.4f  wrote=%d",
        result["communityCount"],
        result["modularity"],
        result["nodePropertiesWritten"],
    )
    return dict(result)


def _normalise_scores(session) -> int:
    """
    Min-max normalise influence_score on Booth nodes to [0, 1] range so the
    frontend heatmap can render relative colours without knowing raw PageRank
    magnitude.
    Returns the number of Booth nodes updated.
    """
    # Fetch min/max
    stats = session.run(
        "MATCH (b:Booth) WHERE b.influence_score IS NOT NULL "
        "RETURN min(b.influence_score) AS mn, max(b.influence_score) AS mx"
    ).single()
    if not stats or stats["mx"] is None or stats["mx"] == stats["mn"]:
        return 0

    mn, mx = float(stats["mn"]), float(stats["mx"])
    span = mx - mn

    result = session.run(
        """
        MATCH (b:Booth)
        WHERE b.influence_score IS NOT NULL
        SET b.influence_score_norm = round((b.influence_score - $mn) / $span, 4)
        RETURN count(b) AS updated
        """,
        mn=mn,
        span=span,
    ).single()
    updated = int(result["updated"]) if result else 0
    logger.info("[gds] Normalised influence scores on %d Booth nodes.", updated)
    return updated


# ── Top-level entry point ─────────────────────────────────────────────────────


def run_influence_analysis(dry_run: bool = False) -> dict:
    """
    Full pipeline:
      1. Project graph
      2. PageRank (writes influence_score to Booth nodes)
      3. Louvain (writes community_id to Booth nodes)
      4. Normalise scores to [0,1]
      5. Drop projection (free GDS memory)

    Args:
        dry_run: If True, only project the graph and report stats without
                 writing any properties.

    Returns:
        dict with keys: graph_stats, pagerank_stats, louvain_stats, normalised
    """
    from backend.db import get_neo4j_session

    results: dict = {}

    with get_neo4j_session() as session:
        # Ensure GDS plugin is available
        try:
            session.run("CALL gds.version() YIELD version").single()
        except Exception as exc:
            logger.error(
                "[gds] GDS plugin unavailable (%s). "
                "Install neo4j-graph-data-science plugin in Neo4j to use this module.",
                exc,
            )
            return {"error": str(exc), "gds_available": False}

        _drop_graph_if_exists(session)

        graph_stats = _project_graph(session)
        results["graph_stats"] = graph_stats

        if not dry_run:
            results["pagerank_stats"] = _run_pagerank(session)
            results["louvain_stats"] = _run_louvain(session)
            results["normalised"] = _normalise_scores(session)
        else:
            logger.info("[gds] dry_run=True — skipping write steps.")
            results["pagerank_stats"] = "skipped (dry_run)"
            results["louvain_stats"] = "skipped (dry_run)"
            results["normalised"] = 0

        # Always release the in-memory projection
        try:
            session.run("CALL gds.graph.drop($name)", name=_GRAPH_NAME)
            logger.info("[gds] Projection '%s' dropped.", _GRAPH_NAME)
        except Exception as exc:
            logger.warning("[gds] Could not drop projection: %s", exc)

    return results


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
        handlers=[logging.StreamHandler()],
    )
    parser = argparse.ArgumentParser(
        description="Run GDS PageRank + Louvain booth influence scoring"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Project graph and report stats without writing properties",
    )
    args = parser.parse_args()

    import json

    out = run_influence_analysis(dry_run=args.dry_run)
    print("\n=== GDS Influence Analysis Results ===")
    print(json.dumps(out, indent=2, default=str))
