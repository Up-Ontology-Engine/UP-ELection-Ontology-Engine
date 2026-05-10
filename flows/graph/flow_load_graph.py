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

import sqlalchemy as sa

logger = logging.getLogger(__name__)


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
