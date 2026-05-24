"""
load_caste_influence.py
========================
Neo4j graph loader for the Surname-Caste Electoral Influence layer.

Creates/updates nodes and relationships:

Nodes
-----
  (:SurnameGroup {name, social_category, voter_count, population_share, ac_id})
  Uses existing: (:Booth), (:Party), (:Candidate)

Relationships
-------------
  (Booth)-[:HAS_CASTE_COMPOSITION {caste_group, share, n_voters}]->(SurnameGroup)
  (SurnameGroup)-[:CORRELATES_WITH {r, p_value, dominant, swing_potential}]->(Party)
  (Candidate)-[:BELONGS_TO_CASTE {confidence}]->(SurnameGroup)

Usage
-----
  python -m graph.loaders.load_caste_influence
  python -m graph.loaders.load_caste_influence --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
TRANSFORMED = ROOT / "data" / "transformed"


def get_driver():
    try:
        from neo4j import GraphDatabase
    except ImportError:
        raise ImportError("neo4j package not installed. Run: pip install neo4j")
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "gorakhpur123")
    return GraphDatabase.driver(uri, auth=(user, password))


# ── Cypher queries ─────────────────────────────────────────────────────────────

_MERGE_SURNAME_GROUP = """
MERGE (sg:SurnameGroup {name: $name, ac_id: $ac_id})
SET sg.social_category = $social_category,
    sg.voter_count = $voter_count,
    sg.population_share = $population_share,
    sg.dominant_party = $dominant_party,
    sg.swing_potential = $swing_potential,
    sg.n_booths_dominant = $n_booths_dominant,
    sg.candidate_caste_match = $candidate_caste_match
"""

_MERGE_BOOTH_CASTE = """
MATCH (b:Booth {booth_id: $booth_id})
MATCH (sg:SurnameGroup {name: $caste_group, ac_id: $ac_id})
MERGE (b)-[r:HAS_CASTE_COMPOSITION {caste_group: $caste_group}]->(sg)
SET r.share = $share,
    r.n_voters = $n_voters
"""

_MERGE_CASTE_PARTY_CORR = """
MATCH (sg:SurnameGroup {name: $caste_group, ac_id: $ac_id})
MERGE (p:Party {name: $party})
MERGE (sg)-[r:CORRELATES_WITH {party: $party}]->(p)
SET r.pearson_r = $pearson_r,
    r.p_value = $p_value,
    r.dominant = $dominant,
    r.swing_potential = $swing_potential
"""

_MERGE_CANDIDATE_CASTE = """
MATCH (c:Candidate {pid: $pid})
MATCH (sg:SurnameGroup {name: $caste_group, ac_id: $ac_id})
MERGE (c)-[r:BELONGS_TO_CASTE]->(sg)
SET r.confidence = $confidence,
    r.candidate_surname = $candidate_surname
"""

_CREATE_INDEXES = """
CREATE INDEX surname_group_idx IF NOT EXISTS FOR (sg:SurnameGroup) ON (sg.name, sg.ac_id)
"""


# ── Loader ─────────────────────────────────────────────────────────────────────

class CasteInfluenceLoader:
    def __init__(self, driver, ac_number: int = 322, dry_run: bool = False):
        self.driver = driver
        self.ac_id = f"GKP_{ac_number}"
        self.ac_number = ac_number
        self.dry_run = dry_run

    def run(self) -> dict:
        stats = {"surname_groups": 0, "booth_rels": 0, "corr_rels": 0, "candidate_rels": 0}

        scores_path = TRANSFORMED / "caste_influence_scores.json"
        analysis_path = TRANSFORMED / "caste_booth_analysis.parquet"

        if not scores_path.exists():
            log.error("Influence scores not found: %s — run the pipeline first", scores_path)
            return stats

        with open(scores_path, encoding="utf-8") as fh:
            all_scores = json.load(fh)

        ac_key = f"ac_{self.ac_number}"
        ac_scores = all_scores.get(ac_key, {})
        if not ac_scores:
            log.error("No scores found for %s", ac_key)
            return stats

        if self.dry_run:
            log.info("[DRY RUN] Would load %d caste groups for %s", len(ac_scores), ac_key)
            return stats

        with self.driver.session() as session:
            # Indexes
            session.run(_CREATE_INDEXES)

            # ── 1: Create SurnameGroup nodes ────────────────────────────────
            log.info("Loading %d SurnameGroup nodes…", len(ac_scores))
            for caste_name, info in ac_scores.items():
                session.run(
                    _MERGE_SURNAME_GROUP,
                    name=caste_name,
                    ac_id=self.ac_id,
                    social_category=info.get("social_category") or "Unknown",
                    voter_count=info.get("n_voters") or 0,
                    population_share=info.get("population_share") or 0.0,
                    dominant_party=info.get("dominant_party") or "",
                    swing_potential=info.get("swing_potential") or "Unknown",
                    n_booths_dominant=info.get("n_booths_dominant") or 0,
                    candidate_caste_match=bool(info.get("candidate_caste_match")),
                )
                stats["surname_groups"] += 1

            # ── 2: Booth–Caste composition relationships ─────────────────────
            if analysis_path.exists():
                import pandas as pd
                df = pd.read_parquet(analysis_path)
                caste_cols = [c for c in df.columns if c.startswith("caste_share_")]
                voter_col = "voter_roll_count"

                log.info("Loading %d booth × caste composition relationships…", len(df) * len(caste_cols))
                for _, row in df.iterrows():
                    booth_id = f"{self.ac_id}_{int(row['part_number']):03d}"
                    for col in caste_cols:
                        caste = col.replace("caste_share_", "")
                        share = float(row[col]) if not pd.isna(row[col]) else 0.0
                        if share < 0.005:  # Skip negligible presence
                            continue
                        n_voters = int(share * (row.get(voter_col) or 0))
                        try:
                            session.run(
                                _MERGE_BOOTH_CASTE,
                                booth_id=booth_id,
                                caste_group=caste,
                                ac_id=self.ac_id,
                                share=share,
                                n_voters=n_voters,
                            )
                            stats["booth_rels"] += 1
                        except Exception as e:
                            log.debug("Booth rel skipped (booth not in graph): %s", e)

            # ── 3: Caste–Party correlation relationships ──────────────────────
            log.info("Loading caste–party correlation relationships…")
            for caste_name, info in ac_scores.items():
                party_keys = {
                    k.replace("pearson_r_", "")
                    for k in info.keys()
                    if k.startswith("pearson_r_")
                }
                dominant = info.get("dominant_party")
                swing = info.get("swing_potential") or "Unknown"

                for party in party_keys:
                    r_val = info.get(f"pearson_r_{party}")
                    p_val = info.get(f"p_value_{party}")
                    if r_val is None:
                        continue
                    session.run(
                        _MERGE_CASTE_PARTY_CORR,
                        caste_group=caste_name,
                        ac_id=self.ac_id,
                        party=party,
                        pearson_r=float(r_val),
                        p_value=float(p_val) if p_val else None,
                        dominant=(party == dominant),
                        swing_potential=swing,
                    )
                    stats["corr_rels"] += 1

            # ── 4: Candidate–Caste relationships ─────────────────────────────
            cand_path = TRANSFORMED / "candidates_normalized.parquet"
            if cand_path.exists():
                import pandas as pd
                from analytics.surname_caste.caste_mapper import CasteMapper
                mapper = CasteMapper(use_llm=False)

                cands = pd.read_parquet(cand_path)
                cands = cands[cands["constituency_no"] == str(self.ac_number)]
                log.info("Loading %d candidate–caste relationships…", len(cands))

                for _, row in cands.iterrows():
                    pid = str(row.get("pid") or "")
                    if not pid:
                        continue
                    surname = str(row.get("candidate_surname") or "")
                    info = mapper.lookup(surname)
                    cg = info.get("caste_group", "Unknown")
                    conf = info.get("confidence", "low")
                    if cg == "Unknown":
                        continue
                    try:
                        session.run(
                            _MERGE_CANDIDATE_CASTE,
                            pid=pid,
                            caste_group=cg,
                            ac_id=self.ac_id,
                            confidence=conf,
                            candidate_surname=surname,
                        )
                        stats["candidate_rels"] += 1
                    except Exception as e:
                        log.debug("Candidate rel skipped: %s", e)

        log.info("Neo4j load complete: %s", stats)
        return stats


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    parser = argparse.ArgumentParser(description="Load caste influence data into Neo4j")
    parser.add_argument("--ac", type=int, default=322)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        driver = get_driver()
        loader = CasteInfluenceLoader(driver, ac_number=args.ac, dry_run=args.dry_run)
        stats = loader.run()
        print("Stats:", stats)
        driver.close()
    except Exception as exc:
        log.exception("Neo4j load failed: %s", exc)


if __name__ == "__main__":
    main()
