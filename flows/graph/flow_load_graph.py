"""
Orchestrator: Full graph load — ETL → Postgres → Neo4j

Runs all ETL transforms (Postgres staging) then all Neo4j loaders in dependency order.

Usage:
  python -m flows.graph.flow_load_graph             # full run
  python -m flows.graph.flow_load_graph --stage etl # ETL only (Postgres staging)
  python -m flows.graph.flow_load_graph --stage neo4j # Neo4j only (assumes Postgres populated)
"""
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

import sqlalchemy as sa

logger = logging.getLogger(__name__)


def _apply_constraints_v2(session) -> dict[str, int | bool]:
    """Apply graph/constraints_v2.cypher at runtime (non-destructive IF NOT EXISTS)."""
    constraints_path = Path(__file__).resolve().parents[2] / "graph" / "constraints_v2.cypher"
    if not constraints_path.exists():
        logger.warning("constraints_v2.cypher not found at %s", constraints_path)
        return {"enabled": False, "statements": 0}

    content = constraints_path.read_text(encoding="utf-8")
    statements: list[str] = []
    for raw in content.split(";"):
        lines = []
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue
            lines.append(line)
        stmt = "\n".join(lines).strip()
        if stmt:
            statements.append(stmt)

    applied = 0
    for stmt in statements:
        session.run(stmt)
        applied += 1

    logger.info("Applied constraints_v2.cypher statements: %d", applied)
    return {"enabled": True, "statements": applied}


def _run_loader_hardening_checks(session) -> dict[str, int]:
    """Run non-destructive graph hardening audits after load."""
    checks = {
        "pulse_events_without_booth": "MATCH (pe:PulseEvent) WHERE NOT (pe)-[:AT_BOOTH]->(:Booth) RETURN count(pe) AS c",
        "booths_without_ac": "MATCH (b:Booth) WHERE NOT ()-[:HAS_BOOTH]->(b) RETURN count(b) AS c",
        "narratives_without_issue": "MATCH (n:Narrative) WHERE NOT (n)-[:ABOUT_ISSUE]->(:Issue) RETURN count(n) AS c",
        "scheme_gaps_without_scheme": "MATCH (sg:SchemeGap) WHERE NOT (sg)-[:FOR_SCHEME]->(:Scheme) RETURN count(sg) AS c",
        "contradictions_without_entity": "MATCH (cf:ContradictionFlag) WHERE NOT (cf)-[:ABOUT_ENTITY]->(:Party) AND NOT (cf)-[:ABOUT_ENTITY]->(:Candidate) RETURN count(cf) AS c",
    }
    out: dict[str, int] = {}
    for key, query in checks.items():
        record = session.run(query).single()
        out[key] = int(record["c"] if record else 0)
    logger.info("Graph hardening audit: %s", out)
    return out


def run_etl_stage(_engine: sa.Engine) -> None:
    """Stage 1: Transform raw files → Postgres."""
    logger.info("=== ETL STAGE: Raw files → Postgres ===")

    from etl.transform_geography   import run as geo_run
    from etl.transform_candidates  import run as cand_run
    from etl.transform_panchayats  import run as pan_run
    from etl.transform_schemes     import run as scheme_run
    from etl.transform_news        import run as news_run
    from etl.ingest_youtube_videos import run as yt_run
    from etl.seed_known_candidates import run as seed_cand_run

    geo_run()
    logger.info("[1/7] Geography done")

    cand_run()
    logger.info("[2/7] Candidates done")

    seed_cand_run()
    logger.info("[3/7] Candidate affidavit seed done")

    pan_run()
    logger.info("[4/7] Panchayats done")

    scheme_run()
    logger.info("[5/7] Schemes done")

    news_run()
    logger.info("[6/7] News staging done")

    yt_run()
    logger.info("[7/7] YouTube videos ingested")

    # Census is optional (requires gorakhpur_aliases.json populated)
    try:
        from etl.transform_census import run as census_run
        census_run()
        logger.info("[+] Census enrichment done")
    except Exception as e:
        logger.warning("Census ETL skipped (likely aliases not yet set): %s", e)


def run_neo4j_stage() -> None:
    """Stage 2: Load Postgres data → Neo4j graph."""
    logger.info("=== NEO4J STAGE: Postgres → Graph ===")

    from api.db import get_pg_engine, get_neo4j_session
    from graph.loaders.load_structure          import load_all as load_structure
    from graph.loaders.load_candidates         import load_all as load_candidates
    from graph.loaders.load_results            import load_all as load_results
    from graph.loaders.load_panchayats         import load_all as load_panchayats
    from graph.loaders.load_mla_works          import load_all as load_mla_works
    from graph.loaders.load_pulse_events       import load_pulse_events
    from graph.loaders.load_quality_narratives import load_all as load_intelligence
    from graph.loaders.load_youtube            import load_all as load_youtube

    pg = get_pg_engine()

    with get_neo4j_session() as session:
        counts = {}

        counts["constraints_v2"] = _apply_constraints_v2(session)

        # MUST run first — all other nodes reference State/District/AC/Booth
        counts["structure"] = load_structure(pg, session)
        logger.info("[1/7] Structure loaded: %s", counts["structure"])

        counts["candidates"] = load_candidates(pg, session)
        logger.info("[2/7] Candidates loaded: %s", counts["candidates"])

        counts["results"] = load_results(pg, session)
        logger.info("[3/7] Election results loaded: %s", counts["results"])

        counts["panchayats"] = load_panchayats(pg, session)
        logger.info("[4/7] Panchayats loaded: %s", counts["panchayats"])

        counts["mla_works"] = load_mla_works(pg, session)
        logger.info("[5/7] MLA work loaded: %s", counts["mla_works"])

        counts["pulse_events"] = load_pulse_events(pg, session)
        logger.info("[6/8] Pulse events loaded: %d", counts["pulse_events"])

        counts["intelligence"] = load_intelligence(pg, session)
        logger.info("[7/8] Intelligence layer loaded: %s", counts["intelligence"])

        counts["youtube"] = load_youtube(pg, session)
        logger.info("[8/8] YouTube videos loaded: %s", counts["youtube"])

        counts["hardening"] = _run_loader_hardening_checks(session)
        logger.info("[H] Hardening checks: %s", counts["hardening"])

    logger.info("=== NEO4J LOAD COMPLETE: %s ===", counts)


def run(stage: str = "all") -> None:
    engine = sa.create_engine(os.environ["POSTGRES_URL"])

    if stage in ("all", "etl"):
        run_etl_stage(engine)

    if stage in ("all", "neo4j"):
        run_neo4j_stage()

    logger.info("=== flow_load_graph complete ===")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["all", "etl", "neo4j"], default="all")
    args = parser.parse_args()
    run(args.stage)
