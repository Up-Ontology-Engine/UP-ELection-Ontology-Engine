"""
Neo4j loader — Affidavit intelligence for Candidates

Reads candidate_affidavits from Postgres and creates:
  (:Candidate)-[:HAS_CRIMINAL_RECORD]->(:CriminalRecord)
  (:Candidate)-[:HAS_ASSETS]->(:AssetDeclaration)

Also enriches Candidate nodes with criminal_cases, net_worth_cr, education, etc.

Run: python -m graph.loaders.load_affidavits
"""
from __future__ import annotations
import logging
from neo4j import Session
import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)


def load_all(pg_engine: sa.Engine, session: Session) -> dict[str, int]:
    with pg_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                ca.candidate_id::text,
                cm.name,
                ca.election_year,
                ca.criminal_cases,
                ca.serious_cases,
                ca.total_assets,
                ca.total_liabilities,
                ca.education,
                ca.profession,
                ca.age
            FROM candidate_affidavits ca
            JOIN candidate_master cm ON cm.candidate_id = ca.candidate_id
            WHERE ca.candidate_id IS NOT NULL
              AND cm.ac_id = 'GKP_322'
        """)).mappings().fetchall()

    if not rows:
        logger.info("No candidate_affidavits rows — run: python -m ingestion.ddp_affidavits")
        return {"affidavits": 0, "criminal_records": 0, "assets": 0}

    criminal_loaded = 0
    asset_loaded = 0

    for r in rows:
        cid  = r["candidate_id"]
        year = r["election_year"] or 2022
        net_worth_cr = round(((r["total_assets"] or 0) - (r["total_liabilities"] or 0)) / 1_00_00_000, 2)

        # Enrich the Candidate node with affidavit properties
        session.run("""
            MATCH (c:Candidate {candidate_id: $cid})
            SET c.criminal_cases   = $criminal,
                c.serious_cases    = $serious,
                c.total_assets_inr = $assets,
                c.net_worth_cr     = $net_worth_cr,
                c.education        = $edu,
                c.profession       = $prof,
                c.age              = $age
        """, {
            "cid":          cid,
            "criminal":     r["criminal_cases"] or 0,
            "serious":      r["serious_cases"] or 0,
            "assets":       r["total_assets"] or 0,
            "net_worth_cr": net_worth_cr,
            "edu":          r["education"] or "",
            "prof":         r["profession"] or "",
            "age":          r["age"],
        })

        # CriminalRecord node (only when cases exist)
        if (r["criminal_cases"] or 0) > 0:
            session.run("""
                MATCH (c:Candidate {candidate_id: $cid})
                MERGE (cr:CriminalRecord {record_id: $cid + '_' + toString($year)})
                SET cr.candidate_id   = $cid,
                    cr.candidate_name = $name,
                    cr.total_cases    = $criminal,
                    cr.serious_cases  = $serious,
                    cr.election_year  = $year
                MERGE (c)-[:HAS_CRIMINAL_RECORD]->(cr)
            """, {
                "cid":      cid,
                "name":     r["name"],
                "year":     year,
                "criminal": r["criminal_cases"],
                "serious":  r["serious_cases"] or 0,
            })
            criminal_loaded += 1

        # AssetDeclaration node (always)
        session.run("""
            MATCH (c:Candidate {candidate_id: $cid})
            MERGE (ad:AssetDeclaration {decl_id: $cid + '_' + toString($year)})
            SET ad.candidate_id   = $cid,
                ad.candidate_name = $name,
                ad.election_year  = $year,
                ad.total_assets   = $assets,
                ad.total_liab     = $liab,
                ad.net_worth_cr   = $net_worth_cr
            MERGE (c)-[:HAS_ASSETS]->(ad)
        """, {
            "cid":          cid,
            "name":         r["name"],
            "year":         year,
            "assets":       r["total_assets"] or 0,
            "liab":         r["total_liabilities"] or 0,
            "net_worth_cr": net_worth_cr,
        })
        asset_loaded += 1

    logger.info(
        "Loaded %d CriminalRecord nodes, %d AssetDeclaration nodes",
        criminal_loaded, asset_loaded,
    )
    return {"affidavits": len(rows), "criminal_records": criminal_loaded, "assets": asset_loaded}


if __name__ == "__main__":
    import logging as _log
    _log.basicConfig(level=_log.INFO, format="%(levelname)s %(message)s")
    from dotenv import load_dotenv; load_dotenv()
    from backend.db import get_pg_engine, get_neo4j_session
    pg = get_pg_engine()
    with get_neo4j_session() as s:
        print(load_all(pg, s))
