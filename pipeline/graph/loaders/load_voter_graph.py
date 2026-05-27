"""
Neo4j loader — Voter-level knowledge graph (from electoral roll records)

Ports the voter-graph building logic from the digital-democracy-pipeline
(``neo4j_ingest.py`` / ``voter_graph.py``) into the *existing* Gorakhpur
knowledge graph, instead of DDP's isolated run-scoped graph.

What it builds:
    (:Voter)-[:RESIDES_AT]->(:Household)-[:IN_SECTION]->(:Section)-[:IN_BOOTH]->(:Booth)
    (:Voter)-[:GUARDIAN {kind, relation}]->(:Voter|:Person)
    (:Voter)-[:CO_RESIDES_WITH]-(:Voter)        (same household, derived)
    (:Voter)-[:SIBLING_OF]-(:Voter)             (shared parent, derived)

Integration with the existing graph:
    DDP models a `Part` per electoral roll; in this repo a *Part* IS a polling
    booth, keyed identically to `booth_master`/`load_structure`:
        booth_id = f"GKP_{ac_no}_{part_no:03d}"   (e.g. "GKP_322_045")
        ac_id    = f"GKP_{ac_no}"                 (e.g. "GKP_322")
    So Voter→Household→Section attach under the booths already loaded by
    `graph.loaders.load_structure`, which in turn hang under the AC.

Identity / family / normalization logic is reused directly from the DDP package
(`_norm_name`, `ontology.family_relation`, `entity_resolution.best_name_match`)
so behavior matches the upstream pipeline. Connection uses the repo-standard
`api.db.get_neo4j_session()` (NOT DDP's neo4j_client).

Idempotent: Voters are keyed by EPIC (or a stable synthetic key), so re-running
the same roll yields the same graph.

Run:
    # From extracted records JSON (no OCR cost):
    python -m graph.loaders.load_voter_graph --records data/ddp_runs/roll_a/records.json --ac 322

    # End-to-end from a PDF (requires SARVAM_API_KEY; OCR cost):
    python -m graph.loaders.load_voter_graph --pdf "path/to/roll.pdf" --ac 322 --dump records.json
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from neo4j import Session

logger = logging.getLogger(__name__)


def _ensure_ddp_importable() -> None:
    """Make the sibling digital-democracy-pipeline package importable.

    Works whether it's pip-installed or only present as source in this monorepo.
    NOTE: DDP targets Python 3.11+ (uses ``enum.StrEnum``); run under a 3.11+ env.
    """
    try:
        import digital_democracy_pipeline  # noqa: F401

        return
    except ImportError:
        src = Path(__file__).resolve().parents[2] / "digital-democracy-pipeline" / "src"
        if src.is_dir():
            sys.path.insert(0, str(src))


_ensure_ddp_importable()

# DDP backend logic, reused verbatim so identity/family/normalization match upstream.
from digital_democracy_pipeline import ontology  # noqa: E402

# noqa: E402
from digital_democracy_pipeline.entity_resolution import best_name_match  # noqa: E402
from digital_democracy_pipeline.voter_graph import (
    _CORESIDENCE_HOUSEHOLD_CAP,
    _norm_name,
)

_CONSTRAINTS = [
    "CREATE CONSTRAINT voter_key IF NOT EXISTS FOR (v:Voter) REQUIRE v.voter_key IS UNIQUE",
    "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT booth_id_unique IF NOT EXISTS FOR (b:Booth) REQUIRE b.id IS UNIQUE",
    "CREATE INDEX voter_epic IF NOT EXISTS FOR (v:Voter) ON (v.epic_id)",
    "CREATE INDEX voter_norm IF NOT EXISTS FOR (v:Voter) ON (v.name_norm)",
    "CREATE INDEX voter_booth IF NOT EXISTS FOR (v:Voter) ON (v.booth_id)",
    "CREATE INDEX household_id IF NOT EXISTS FOR (h:Household) ON (h.id)",
    "CREATE INDEX section_id IF NOT EXISTS FOR (s:Section) ON (s.id)",
]


# ── Record → row transformation (existing-graph keys) ────────────────────────


def _g(rec: dict[str, Any], key: str) -> str:
    return str(rec.get(key) or "").strip()


def _as_dict(rec: Any) -> dict[str, Any]:
    if hasattr(rec, "to_dict"):
        return rec.to_dict()
    if isinstance(rec, dict):
        return rec
    # dataclass / arbitrary object fallback
    return {
        k: getattr(rec, k)
        for k in dir(rec)
        if not k.startswith("_") and not callable(getattr(rec, k))
    }


def _digits(s: str) -> str:
    return re.sub(r"[^\d]", "", s or "")


def records_to_rows(records: list[Any], ac_default: int | None = None) -> list[dict[str, Any]]:
    """Map ElectoralRollRecord(s)/dicts to ingestion rows keyed for the existing graph."""
    rows: list[dict[str, Any]] = []
    skipped = 0
    for i, raw in enumerate(records):
        rec = _as_dict(raw)
        epic = _g(rec, "epic_id")
        ac_digits = _digits(_g(rec, "assembly_constituency_no")) or (
            str(ac_default) if ac_default else ""
        )
        part_digits = _digits(_g(rec, "part_no"))

        if not (ac_digits and part_digits):
            # Cannot place under a booth in the existing hierarchy — skip geo, but
            # voters without a part are not useful for this graph. Track + drop.
            skipped += 1
            continue

        ac_no = int(ac_digits)
        part_no = int(part_digits)
        ac_id = f"GKP_{ac_no}"
        booth_id = f"GKP_{ac_no}_{part_no:03d}"
        section = _g(rec, "section_no")
        house = _g(rec, "house_number")
        guardian = _g(rec, "guardian_name")

        ident = epic or f"SYN:{ac_no}:{part_no}:{_g(rec, 'serial_no') or i}"
        rows.append(
            {
                "key": f"voter::{ident}",
                "epic_id": epic,
                "epic_synthetic": not epic,
                "serial_no": _g(rec, "serial_no"),
                "name": _g(rec, "name"),
                "name_norm": _norm_name(rec.get("name")),
                "age": _g(rec, "age"),
                "gender": _g(rec, "gender"),
                "deleted": bool(rec.get("deleted")),
                "deletion_reason_code": _g(rec, "deletion_reason_code"),
                "deletion_reason": _g(rec, "deletion_reason"),
                "house_number": house,
                "part_no": part_no,
                "section_no": section,
                "section_name": _g(rec, "section_name"),
                "ac_id": ac_id,
                "ac_name": _g(rec, "assembly_constituency_name"),
                "booth_id": booth_id,
                "guardian_name": guardian,
                "guardian_norm": _norm_name(guardian),
                "guardian_relation": _g(rec, "guardian_relation"),
                "guardian_kind": ontology.family_relation(rec.get("guardian_relation")),
                "section_id": f"{booth_id}|{section}" if section else "",
                "house_id": f"{booth_id}|{section}|{house}" if house else "",
            }
        )

    # Flag duplicate EPICs (same EPIC on multiple source records).
    epic_counts = Counter(r["epic_id"] for r in rows if r["epic_id"])
    for r in rows:
        r["source_count"] = epic_counts.get(r["epic_id"], 1) if r["epic_id"] else 1

    if skipped:
        logger.warning("%d records had no parseable AC/part_no — skipped", skipped)
    return rows


def _batches(rows: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


# ── Cypher ───────────────────────────────────────────────────────────────────

_Q_VOTERS = """
UNWIND $rows AS r
MERGE (v:Voter {voter_key: r.key})
SET v.epic_id=r.epic_id, v.epic_synthetic=r.epic_synthetic, v.serial_no=r.serial_no,
    v.name=r.name, v.name_norm=r.name_norm, v.age=r.age, v.gender=r.gender,
    v.deleted=r.deleted, v.deletion_reason_code=r.deletion_reason_code,
    v.deletion_reason=r.deletion_reason, v.house_number=r.house_number,
    v.part_no=r.part_no, v.section_no=r.section_no, v.ac_id=r.ac_id, v.booth_id=r.booth_id,
    v.guardian_name=r.guardian_name, v.guardian_norm=r.guardian_norm,
    v.guardian_relation=r.guardian_relation, v.guardian_kind=r.guardian_kind,
    v.source_count=r.source_count
"""

_Q_RESIDES = """
UNWIND $rows AS r
MATCH (v:Voter {voter_key: r.key})
MERGE (h:Household {id: r.house_id}) SET h.house_number=r.house_number, h.booth_id=r.booth_id
MERGE (v)-[:RESIDES_AT]->(h)
"""

_Q_HOUSE_SECTION = """
UNWIND $rows AS r
MERGE (h:Household {id: r.house_id})
MERGE (s:Section {id: r.section_id}) SET s.section_no=r.section_no, s.section_name=r.section_name, s.booth_id=r.booth_id
MERGE (h)-[:IN_SECTION]->(s)
"""

# Section attaches to the EXISTING Booth (booth_id matches booth_master/load_structure).
# Booth/AC are MERGEd defensively so the voter subgraph is connected even if the
# structure loader hasn't seeded that part yet; existing nodes are reused, never overwritten.
_Q_SECTION_BOOTH = """
UNWIND $rows AS r
MERGE (s:Section {id: r.section_id})
MERGE (b:Booth {booth_id: r.booth_id})
  ON CREATE SET b.booth_number=r.part_no, b.ac_id=r.ac_id
MERGE (ac:AssemblyConstituency {ac_id: r.ac_id})
  ON CREATE SET ac.name=r.ac_name
MERGE (ac)-[:HAS_BOOTH]->(b)
MERGE (s)-[:IN_BOOTH]->(b)
"""

_Q_GUARDIAN_VOTER = """
UNWIND $rows AS r
MATCH (v:Voter {voter_key: r.vkey})
MATCH (g:Voter {voter_key: r.gkey})
MERGE (v)-[rel:GUARDIAN]->(g)
SET rel.kind=r.kind, rel.relation=r.relation
"""

_Q_GUARDIAN_PERSON = """
UNWIND $rows AS r
MATCH (v:Voter {voter_key: r.vkey})
MERGE (p:Person {id: r.pid}) SET p.name=r.pname
MERGE (v)-[rel:GUARDIAN]->(p)
SET rel.kind=r.kind, rel.relation=r.relation
"""

# Derived voter↔voter edges, scoped to the booths touched in this run.
_Q_CORESIDES = """
MATCH (b:Booth)<-[:IN_BOOTH]-(:Section)<-[:IN_SECTION]-(h:Household)<-[:RESIDES_AT]-(v:Voter)
WHERE b.booth_id IN $booths
WITH h, collect(v) AS residents
WHERE size(residents) >= 2 AND size(residents) <= $cap
UNWIND range(0, size(residents)-2) AS i
UNWIND range(i+1, size(residents)-1) AS j
WITH residents[i] AS a, residents[j] AS c
MERGE (a)-[:CO_RESIDES_WITH]-(c)
"""

_Q_SIBLINGS = """
MATCH (g)<-[gr:GUARDIAN]-(c:Voter)
WHERE gr.kind IN ['FATHER_OF','MOTHER_OF'] AND c.booth_id IN $booths
WITH g, collect(DISTINCT c) AS kids
WHERE size(kids) >= 2 AND size(kids) <= $cap
UNWIND range(0, size(kids)-2) AS i
UNWIND range(i+1, size(kids)-1) AS j
WITH kids[i] AS a, kids[j] AS b
MERGE (a)-[:SIBLING_OF]-(b)
"""


def _link_guardians(
    session: Session, rows: list[dict[str, Any]], batch_size: int
) -> dict[str, int]:
    """Resolve each guardian to a Voter (exact, then fuzzy within the same booth/part)
    and write the GUARDIAN edge; unmatched guardians become :Person nodes."""
    norms_by_part: dict[int, list[str]] = {}
    key_by_norm_part: dict[tuple[int, str], str] = {}
    for r in rows:
        if r["name_norm"]:
            key_by_norm_part.setdefault((r["part_no"], r["name_norm"]), r["key"])
            lst = norms_by_part.setdefault(r["part_no"], [])
            if r["name_norm"] not in lst:
                lst.append(r["name_norm"])

    voter_links: list[dict[str, Any]] = []
    person_links: list[dict[str, Any]] = []
    for r in rows:
        gnorm = r["guardian_norm"]
        if not gnorm:
            continue
        part = r["part_no"]
        target = key_by_norm_part.get((part, gnorm))
        if target is None:
            candidates = [n for n in norms_by_part.get(part, []) if n != r["name_norm"]]
            matched = best_name_match(gnorm, candidates)
            if matched:
                target = key_by_norm_part.get((part, matched))
        if target and target != r["key"]:
            voter_links.append(
                {
                    "vkey": r["key"],
                    "gkey": target,
                    "kind": r["guardian_kind"],
                    "relation": r["guardian_relation"],
                }
            )
        else:
            person_links.append(
                {
                    "vkey": r["key"],
                    "pid": f"person::{part}::{gnorm}",
                    "pname": r["guardian_name"],
                    "kind": r["guardian_kind"],
                    "relation": r["guardian_relation"],
                }
            )
    for batch in _batches(voter_links, batch_size):
        session.run(_Q_GUARDIAN_VOTER, rows=batch)
    for batch in _batches(person_links, batch_size):
        session.run(_Q_GUARDIAN_PERSON, rows=batch)
    return {"guardian_voter": len(voter_links), "guardian_person": len(person_links)}


def ingest_rows(
    session: Session, rows: list[dict[str, Any]], *, batch_size: int = 500
) -> dict[str, Any]:
    """Ingest pre-built rows into the existing Neo4j graph (idempotent)."""
    for stmt in _CONSTRAINTS:
        session.run(stmt)

    for batch in _batches(rows, batch_size):
        session.run(_Q_VOTERS, rows=batch)

    for q, predicate in (
        (_Q_RESIDES, lambda r: r["house_id"]),
        (_Q_HOUSE_SECTION, lambda r: r["house_id"] and r["section_id"]),
        (_Q_SECTION_BOOTH, lambda r: r["section_id"] and r["booth_id"]),
    ):
        filtered = [r for r in rows if predicate(r)]
        for batch in _batches(filtered, batch_size):
            session.run(q, rows=batch)

    counts = _link_guardians(session, rows, batch_size)

    booths = sorted({r["booth_id"] for r in rows if r["booth_id"]})
    session.run(_Q_CORESIDES, booths=booths, cap=_CORESIDENCE_HOUSEHOLD_CAP)
    session.run(_Q_SIBLINGS, booths=booths, cap=_CORESIDENCE_HOUSEHOLD_CAP)

    result = {"voters": len(rows), "booths": len(booths), **counts}
    logger.info("Voter graph ingest complete: %s", result)
    return result


def ingest_records(
    records: list[Any], *, ac_default: int | None = None, batch_size: int = 500
) -> dict[str, Any]:
    """Build rows from electoral records and ingest into the existing graph."""
    from backend.db import get_neo4j_session

    rows = records_to_rows(records, ac_default=ac_default)
    if not rows:
        logger.warning("No ingestable rows (no records with AC + part_no).")
        return {"voters": 0}
    with get_neo4j_session() as session:
        return ingest_rows(session, rows, batch_size=batch_size)


# ── Record sources ────────────────────────────────────────────────────────────


def _load_records_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text())
    if isinstance(data, dict) and "records" in data:
        data = data["records"]
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON list of records (or {{'records': [...]}})")
    return data


def _extract_from_pdf(pdf: Path, ac: int, dump: Path | None) -> list[Any]:
    """Run the DDP OCR + extraction pipeline (reuses ingestion.ddp_electoral_roll)."""
    from ingestion.ddp_electoral_roll import RUNS_DIR, extract_records_from_pdf

    records = extract_records_from_pdf(pdf, RUNS_DIR / pdf.stem)
    if dump:
        dump.write_text(json.dumps([_as_dict(r) for r in records], ensure_ascii=False, indent=2))
        logger.info("Wrote %d records to %s", len(records), dump)
    return records


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(
        description="Ingest electoral-roll voter graph into the existing Neo4j KG"
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--records", type=Path, help="Path to extracted records JSON (no OCR)")
    src.add_argument(
        "--pdf",
        type=Path,
        help="Path to electoral roll PDF (runs Sarvam OCR; needs SARVAM_API_KEY)",
    )
    p.add_argument(
        "--ac", type=int, default=None, help="AC number fallback when records omit it (e.g. 322)"
    )
    p.add_argument(
        "--dump",
        type=Path,
        default=None,
        help="With --pdf: also write extracted records to this JSON",
    )
    p.add_argument("--batch-size", type=int, default=500)
    args = p.parse_args()

    if args.records:
        recs = _load_records_json(args.records)
    else:
        if args.ac is None:
            p.error("--ac is required with --pdf")
        recs = _extract_from_pdf(args.pdf, args.ac, args.dump)

    summary = ingest_records(recs, ac_default=args.ac, batch_size=args.batch_size)
    logger.info("Done: %s", summary)
