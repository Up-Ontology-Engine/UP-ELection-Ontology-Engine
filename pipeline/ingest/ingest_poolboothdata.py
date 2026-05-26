"""
PoolBoothData_JSON → Neo4j + Postgres ingestion pipeline.

Reads all 177 JSON files from data/PoolBoothData_JSON/ (converted from Hindi
electoral-roll PDFs via scripts/pdf_to_json.py) and ingests them into:

  Neo4j   — Full voter-graph:
              (:Voter)-[:RESIDES_AT]->(:Household)-[:IN_SECTION]->(:Section)
                      -[:IN_BOOTH]->(:Booth)-[:IS_IN]->(:AssemblyConstituency)
              (:Voter)-[:GUARDIAN {kind, relation}]->(:Voter|:Person)
              (:Voter)-[:CO_RESIDES_WITH]-(:Voter)    (same household)
              (:Voter)-[:SIBLING_OF]-(:Voter)          (shared parent)

  Postgres — booth_master voter-count columns:
              male_voters, female_voters, other_voters, total_voters
              (aggregated from the JSON gender fields per part_no)

JSON voter-record keys   →   DDP / loader keys
----------------------------------------------------------------------
voter_id                 →   epic_id
part_number              →   part_no          (from record)
section_number           →   section_no
section_name             →   section_name
name                     →   name
relation_type            →   guardian_relation
relation_name            →   guardian_name
house_number             →   house_number
age                      →   age
gender                   →   gender
(file metadata)          →   assembly_constituency_no  (322)
(file metadata)          →   assembly_constituency_name

Run:
  # Dry-run — transform + print stats, no DB writes:
  python -m ingestion.ingest_poolboothdata --dry-run

  # Neo4j only:
  python -m ingestion.ingest_poolboothdata --neo4j

  # Postgres only:
  python -m ingestion.ingest_poolboothdata --postgres

  # Full pipeline (default):
  python -m ingestion.ingest_poolboothdata

  # Specific files only:
  python -m ingestion.ingest_poolboothdata --parts 1 2 3

Environment:
  NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
  POSTGRES_URL
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ROOT       = Path(__file__).parents[1]
JSON_DIR   = ROOT / "data" / "PoolBoothData_JSON"
AC_DEFAULT = 322
AC_NAME    = "Gorakhpur City"
AC_ID      = f"GKP_{AC_DEFAULT}"


# ── Make the loader importable ────────────────────────────────────────────────

def _setup_paths() -> None:
    """Add repo root and DDP src to sys.path."""
    root = str(ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    ddp_src = ROOT / "digital-democracy-pipeline" / "src"
    if ddp_src.is_dir():
        ddp_str = str(ddp_src)
        if ddp_str not in sys.path:
            sys.path.insert(0, ddp_str)

_setup_paths()

from graph.loaders.load_voter_graph import records_to_rows, ingest_rows  # noqa: E402


# ── Gender normalisation (matches the PDF pipeline's output) ─────────────────

_GENDER_MAP = {
    "male": "M", "m": "M", "पुरुष": "M",
    "female": "F", "f": "F", "महिला": "F", "woman": "F",
    "other": "O", "o": "O", "अन्य": "O",
}

def _norm_gender(raw: str | None) -> str:
    return _GENDER_MAP.get((raw or "").strip().lower(), raw or "")


# ── JSON record → DDP-compatible dict ────────────────────────────────────────

def transform_voter(v: dict[str, Any], ac_no: int, ac_name: str) -> dict[str, Any]:
    """Convert one PoolBoothData_JSON voter record to the DDP dict format
    that records_to_rows() expects."""
    return {
        "epic_id":                   (v.get("voter_id") or "").strip(),
        "serial_no":                 str(v.get("serial_no") or ""),
        "assembly_constituency_no":  str(ac_no),
        "assembly_constituency_name": ac_name,
        "part_no":                   str(v.get("part_number") or ""),
        "section_no":                str(v.get("section_number") or ""),
        "section_name":              (v.get("section_name") or "").strip(),
        "name":                      (v.get("name") or "").strip(),
        "guardian_name":             (v.get("relation_name") or "").strip(),
        "guardian_relation":         (v.get("relation_type") or "").strip(),
        "house_number":              str(v.get("house_number") or "").strip(),
        "age":                       str(v.get("age") or ""),
        "gender":                    _norm_gender(v.get("gender")),
        "deleted":                   False,
        "deletion_reason_code":      "",
        "deletion_reason":           "",
    }


# ── File loading ──────────────────────────────────────────────────────────────

def load_json_files(parts: list[int] | None = None) -> tuple[list[dict], list[dict]]:
    """Load and transform all (or selected) JSON files.

    Returns:
        (all_dicts, all_records)  where all_dicts are the raw voter dicts
        for Postgres aggregation, and all_records are DDP-format dicts
        ready for records_to_rows().
    """
    files = sorted(JSON_DIR.glob("part_*.json"))
    if parts:
        part_set = {f"part_{p:03d}.json" for p in parts}
        files = [f for f in files if f.name in part_set]

    if not files:
        raise FileNotFoundError(f"No JSON files found in {JSON_DIR}")

    all_raw: list[dict] = []
    all_ddp: list[dict] = []
    total_files = len(files)

    for i, path in enumerate(files, 1):
        data = json.loads(path.read_text(encoding="utf-8"))
        meta = data.get("metadata", {})
        ac_no   = meta.get("assembly_constituency", {}).get("number", AC_DEFAULT)
        ac_name = meta.get("assembly_constituency", {}).get("name", AC_NAME)

        voters = data.get("voter_records", [])
        for idx, v in enumerate(voters):
            # Inject a serial_no if missing (position within the file)
            if not v.get("serial_no"):
                v = {**v, "serial_no": idx + 1}
            all_raw.append(v)
            all_ddp.append(transform_voter(v, ac_no, ac_name))

        if i % 20 == 0 or i == total_files:
            logger.info("  Loaded %d / %d files — %d records so far",
                        i, total_files, len(all_ddp))

    logger.info("Total: %d voter records from %d files", len(all_ddp), total_files)
    return all_raw, all_ddp


# ── Neo4j ingestion ───────────────────────────────────────────────────────────

def run_neo4j(ddp_records: list[dict], batch_size: int = 500) -> None:
    from backend.db import get_neo4j_session

    logger.info("Transforming %d records into Neo4j row format…", len(ddp_records))
    rows = records_to_rows(ddp_records, ac_default=AC_DEFAULT)
    logger.info("  → %d rows to ingest (after part-filter drops)", len(rows))

    with get_neo4j_session() as session:
        stats = ingest_rows(session, rows, batch_size=batch_size)
    logger.info("Neo4j ingestion complete: %s", stats)


# ── Postgres booth_master sync ────────────────────────────────────────────────

def run_postgres(raw_records: list[dict]) -> None:
    from backend.db import get_pg_engine
    import sqlalchemy as sa
    from sqlalchemy import text

    # Aggregate by part_number
    counts: dict[int, dict[str, int]] = defaultdict(lambda: {"M": 0, "F": 0, "O": 0})
    for v in raw_records:
        part = int(v.get("part_number") or 0)
        if part == 0:
            continue
        g = _norm_gender(v.get("gender"))
        counts[part][g] = counts[part].get(g, 0) + 1

    logger.info("Updating booth_master for %d parts…", len(counts))
    engine = get_pg_engine()

    upsert_sql = text("""
        INSERT INTO booth_master
            (booth_id, ac_id, booth_number, male_voters, female_voters,
             other_voters, total_voters)
        VALUES
            (:booth_id, :ac_id, :booth_number, :male, :female, :other, :total)
        ON CONFLICT (booth_id) DO UPDATE
            SET male_voters   = EXCLUDED.male_voters,
                female_voters = EXCLUDED.female_voters,
                other_voters  = EXCLUDED.other_voters,
                total_voters  = EXCLUDED.total_voters
    """)

    rows_written = 0
    with engine.begin() as conn:
        for part_no, g in sorted(counts.items()):
            booth_id = f"GKP_{AC_DEFAULT}_{part_no:03d}"
            conn.execute(upsert_sql, {
                "booth_id":    booth_id,
                "ac_id":       AC_ID,
                "booth_number": part_no,
                "male":        g.get("M", 0),
                "female":      g.get("F", 0),
                "other":       g.get("O", 0),
                "total":       g.get("M", 0) + g.get("F", 0) + g.get("O", 0),
            })
            rows_written += 1

    logger.info("Postgres: upserted %d booth rows", rows_written)


# ── Dry-run stats ─────────────────────────────────────────────────────────────

def dry_run(raw_records: list[dict], ddp_records: list[dict]) -> None:
    logger.info("=== DRY RUN — no DB writes ===")
    rows = records_to_rows(ddp_records, ac_default=AC_DEFAULT)

    gender_counts: dict[str, int] = defaultdict(int)
    for v in raw_records:
        gender_counts[_norm_gender(v.get("gender"))] += 1

    parts = sorted({int(v.get("part_number") or 0) for v in raw_records if v.get("part_number")})

    print(f"\n{'='*54}")
    print(f"  PoolBoothData_JSON ingestion dry-run")
    print(f"{'='*54}")
    print(f"  Source records : {len(raw_records):,}")
    print(f"  Neo4j rows     : {len(rows):,}")
    print(f"  Parts (booths) : {len(parts)}  ({parts[0]}–{parts[-1]})")
    print(f"  Gender — M:{gender_counts['M']:,}  F:{gender_counts['F']:,}  O:{gender_counts['O']:,}  ?:{gender_counts['']:,}")
    print(f"  AC             : {AC_DEFAULT} — {AC_NAME}")
    print(f"{'='*54}\n")

    # Sample transformed row
    if rows:
        print("Sample Neo4j row:")
        r = rows[0]
        for k, v in r.items():
            print(f"  {k:<22} {v!r}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest PoolBoothData_JSON into Neo4j + Postgres")
    parser.add_argument("--dry-run",  action="store_true", help="Transform only; no DB writes")
    parser.add_argument("--neo4j",    action="store_true", help="Load into Neo4j only")
    parser.add_argument("--postgres", action="store_true", help="Sync booth_master in Postgres only")
    parser.add_argument("--parts",    nargs="+", type=int,  help="Only process these part numbers")
    parser.add_argument("--batch",    type=int, default=500, help="Neo4j batch size (default 500)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    # Default: run both targets
    run_both = not (args.neo4j or args.postgres or args.dry_run)

    logger.info("Loading JSON files from %s …", JSON_DIR)
    raw_records, ddp_records = load_json_files(parts=args.parts)

    if args.dry_run:
        dry_run(raw_records, ddp_records)
        return

    if args.neo4j or run_both:
        run_neo4j(ddp_records, batch_size=args.batch)

    if args.postgres or run_both:
        run_postgres(raw_records)

    logger.info("Pipeline complete.")


if __name__ == "__main__":
    main()
