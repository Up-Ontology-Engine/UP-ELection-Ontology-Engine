# ruff: noqa: E402, F401, F404, F405, F841, F811
"""Startup schema initialization script to execute CREATE CONSTRAINT and CREATE INDEX commands."""

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from backend.db import get_neo4j_session

logger = logging.getLogger(__name__)

CONSTRAINTS = [
    # Core hierarchy & uniqueness
    "CREATE CONSTRAINT IF NOT EXISTS FOR (s:State) REQUIRE s.state_id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (s:State) REQUIRE s.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (d:District) REQUIRE d.district_id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (d:District) REQUIRE d.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (ac:AssemblyConstituency) REQUIRE ac.ac_id IS UNIQUE",
    "CREATE CONSTRAINT unique_booth_id IF NOT EXISTS FOR (b:Booth) REQUIRE b.id IS UNIQUE",
    "CREATE CONSTRAINT unique_party_abbr IF NOT EXISTS FOR (pa:Party) REQUIRE pa.abbreviation IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (b:Booth) REQUIRE b.booth_id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (sec:Section) REQUIRE sec.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (h:Household) REQUIRE h.id IS UNIQUE",
    # Voter & Person
    "CREATE CONSTRAINT IF NOT EXISTS FOR (v:Voter) REQUIRE v.voter_key IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
    # Political actors & attributes
    "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Candidate) REQUIRE c.candidate_id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (pa:Party) REQUIRE pa.party_id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (pa:Party) REQUIRE pa.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Issue) REQUIRE i.code IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Election) REQUIRE e.election_id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (sc:Scheme) REQUIRE sc.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (pan:Panchayat) REQUIRE pan.panchayat_id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (pe:PulseEvent) REQUIRE pe.event_id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (w:WorkItem) REQUIRE w.work_id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (v:YouTubeVideo) REQUIRE v.video_id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (ch:Channel) REQUIRE ch.channel_id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (cr:CriminalRecord) REQUIRE cr.record_id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (ad:AssetDeclaration) REQUIRE ad.decl_id IS UNIQUE",
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS FOR (v:Voter) ON (v.epic_id)",
    "CREATE INDEX IF NOT EXISTS FOR (v:Voter) ON (v.booth_id)",
    "CREATE INDEX IF NOT EXISTS FOR (v:Voter) ON (v.name_norm)",
    "CREATE INDEX IF NOT EXISTS FOR (b:Booth) ON (b.ac_id)",
    "CREATE INDEX IF NOT EXISTS FOR (pe:PulseEvent) ON (pe.mapped_booth_id)",
    "CREATE INDEX IF NOT EXISTS FOR (pe:PulseEvent) ON (pe.mapped_ac_id)",
    "CREATE INDEX IF NOT EXISTS FOR (pe:PulseEvent) ON (pe.issue)",
    "CREATE INDEX IF NOT EXISTS FOR (pe:PulseEvent) ON (pe.entity)",
    "CREATE INDEX IF NOT EXISTS FOR (pe:PulseEvent) ON (pe.created_at)",
    "CREATE INDEX IF NOT EXISTS FOR (c:Candidate) ON (c.ac_id)",
    "CREATE INDEX IF NOT EXISTS FOR (c:Candidate) ON (c.party)",
    "CREATE INDEX IF NOT EXISTS FOR (c:Candidate) ON (c.criminal_cases)",
    "CREATE INDEX IF NOT EXISTS FOR (c:Candidate) ON (c.net_worth_cr)",
    "CREATE INDEX IF NOT EXISTS FOR (v:YouTubeVideo) ON (v.views)",
    "CREATE INDEX IF NOT EXISTS FOR (v:YouTubeVideo) ON (v.query_source)",
    "CREATE INDEX IF NOT EXISTS FOR (cr:CriminalRecord) ON (cr.candidate_id)",
    "CREATE INDEX IF NOT EXISTS FOR (ad:AssetDeclaration) ON (ad.candidate_id)",
]


def initialize_schema():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("Initializing Neo4j schema indexes and constraints...")

    with get_neo4j_session() as session:
        applied_constraints = 0
        applied_indexes = 0

        for stmt in CONSTRAINTS:
            try:
                session.run(stmt)
                applied_constraints += 1
            except Exception as e:
                logger.warning("Constraint creation skipped/failed: %s | Statement: %s", e, stmt)

        for stmt in INDEXES:
            try:
                session.run(stmt)
                applied_indexes += 1
            except Exception as e:
                logger.warning("Index creation skipped/failed: %s | Statement: %s", e, stmt)

        logger.info(
            "Schema initialization complete. Applied %d constraints, %d indexes.",
            applied_constraints,
            applied_indexes,
        )


if __name__ == "__main__":
    initialize_schema()
