"""
Load the pre-scraped Myneta JSON files into Postgres.

Reads:
  data/Myneta/myneta_GKP_322_2022.json
  data/Myneta/myneta_GKP_322_2017.json
  data/Myneta/myneta_GKP_LS64_2024.json

Writes:
  candidate_master        — net_worth_rs, self_profession (UPDATE only existing rows)
  candidate_affidavits    — full upsert: movable/immovable breakdown, ITR JSON,
                            criminal detail JSON, liabilities JSON, source URL
  candidate_party_history — vote result rows (winner, rank, vote share, margin)

Run:
  python pipeline/ingest/load_myneta_json.py
  python pipeline/ingest/load_myneta_json.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).parents[2]
DATA_DIR = ROOT / "data" / "Myneta"

JSON_FILES = [
    DATA_DIR / "myneta_GKP_322_2022.json",
    DATA_DIR / "myneta_GKP_322_2017.json",
    DATA_DIR / "myneta_GKP_LS64_2024.json",
]

POSTGRES_URL = os.environ.get(
    "POSTGRES_URL",
    "postgresql://postgres:postgres@localhost:5432/gorakhpur_db",
)


def _load_all_candidates() -> list[dict]:
    """Read every candidate across all three JSON files."""
    all_cands: list[dict] = []
    for path in JSON_FILES:
        if not path.exists():
            log.warning("JSON file not found: %s — skipping", path)
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        cands = data.get("candidates", [])
        log.info("  %s → %d candidates", path.name, len(cands))
        all_cands.extend(cands)
    return all_cands


def _aff(cand: dict) -> dict:
    return cand.get("affidavit_detail") or {}


def _ls(cand: dict) -> dict:
    return cand.get("list_summary") or {}


def run(dry_run: bool = False) -> None:
    import sqlalchemy as sa
    from sqlalchemy import text

    engine = sa.create_engine(POSTGRES_URL, pool_pre_ping=True)

    log.info("Loading Myneta JSON files from %s …", DATA_DIR)
    candidates = _load_all_candidates()
    log.info("Total candidates across all files: %d", len(candidates))

    aff_upserted = 0
    master_updated = 0
    history_upserted = 0

    with engine.begin() as conn:
        for c in candidates:
            cid = c.get("candidate_id", "").strip()[:40]
            if not cid:
                continue

            aff = _aff(c)
            ls = _ls(c)
            ac_id = c.get("ac_id", "")
            election_year = c.get("election_year") or 0

            # ── 0. ensure candidate_master row exists ──────────────────────
            if not dry_run:
                conn.execute(text("""
                    INSERT INTO candidate_master (
                        candidate_id, name, party, ac_id, election_year,
                        is_incumbent, is_primary_opp,
                        net_worth_rs, self_profession,
                        source_system, source_candidate_id
                    ) VALUES (
                        :cid, :name, :party, :ac_id, :yr,
                        false, false,
                        :net_worth, :profession,
                        'myneta', :src_id
                    )
                    ON CONFLICT (candidate_id) DO NOTHING
                """), {
                    "cid":        cid,
                    "name":       c.get("name", ""),
                    "party":      c.get("party", "IND"),
                    "ac_id":      ac_id,
                    "yr":         election_year,
                    "net_worth":  ((_aff(c).get("movable_assets_rs") or 0)
                                   + (_aff(c).get("immovable_assets_rs") or 0))
                                  or _ls(c).get("total_assets"),
                    "profession": _aff(c).get("profession"),
                    "src_id":     str(c.get("source_candidate_id", "")),
                })

            # ── 1. candidate_affidavits upsert ─────────────────────────────
            movable_rs = aff.get("movable_assets_rs")
            immovable_rs = aff.get("immovable_assets_rs")
            net_worth = (
                (movable_rs or 0) + (immovable_rs or 0)
            ) or ls.get("total_assets")

            parse_status = aff.get("parse_status") or "list_only"
            # If we have itr or movable breakdown, it's fully scraped
            if aff.get("itr_income_json") or aff.get("movable_assets_json"):
                parse_status = "scraped"

            if not dry_run:
                conn.execute(text("""
                    INSERT INTO candidate_affidavits (
                        candidate_id, election_year,
                        criminal_cases, serious_cases,
                        total_assets, total_liabilities,
                        movable_assets_rs, immovable_assets_rs,
                        movable_assets_json, immovable_assets_json,
                        liabilities_json, criminal_case_details_json,
                        itr_income_json,
                        education, age,
                        parse_status, source_affidavit_url,
                        html_snapshot_path, parse_error
                    ) VALUES (
                        :cid, :yr,
                        :criminal, :serious,
                        :total_assets, :total_liab,
                        :movable_rs, :immovable_rs,
                        :movable_json, :immovable_json,
                        :liab_json, :crim_json,
                        :itr_json,
                        :education, :age,
                        :parse_status, :source_url,
                        :snapshot_path, :parse_error
                    )
                    ON CONFLICT (candidate_id) DO UPDATE SET
                        criminal_cases             = EXCLUDED.criminal_cases,
                        serious_cases              = EXCLUDED.serious_cases,
                        total_assets               = EXCLUDED.total_assets,
                        total_liabilities          = EXCLUDED.total_liabilities,
                        movable_assets_rs          = COALESCE(EXCLUDED.movable_assets_rs, candidate_affidavits.movable_assets_rs),
                        immovable_assets_rs        = COALESCE(EXCLUDED.immovable_assets_rs, candidate_affidavits.immovable_assets_rs),
                        movable_assets_json        = COALESCE(EXCLUDED.movable_assets_json, candidate_affidavits.movable_assets_json),
                        immovable_assets_json      = COALESCE(EXCLUDED.immovable_assets_json, candidate_affidavits.immovable_assets_json),
                        liabilities_json           = COALESCE(EXCLUDED.liabilities_json, candidate_affidavits.liabilities_json),
                        criminal_case_details_json = COALESCE(EXCLUDED.criminal_case_details_json, candidate_affidavits.criminal_case_details_json),
                        itr_income_json            = COALESCE(EXCLUDED.itr_income_json, candidate_affidavits.itr_income_json),
                        education                  = COALESCE(EXCLUDED.education, candidate_affidavits.education),
                        age                        = COALESCE(EXCLUDED.age, candidate_affidavits.age),
                        parse_status               = EXCLUDED.parse_status,
                        source_affidavit_url       = COALESCE(EXCLUDED.source_affidavit_url, candidate_affidavits.source_affidavit_url),
                        html_snapshot_path         = COALESCE(EXCLUDED.html_snapshot_path, candidate_affidavits.html_snapshot_path),
                        parse_error                = EXCLUDED.parse_error
                """), {
                    "cid":           cid,
                    "yr":            election_year,
                    "criminal":      ls.get("criminal_cases") or aff.get("criminal_cases") or 0,
                    "serious":       0,
                    "total_assets":  net_worth,
                    "total_liab":    ls.get("liabilities") or 0,
                    "movable_rs":    movable_rs,
                    "immovable_rs":  immovable_rs,
                    "movable_json":  json.dumps(aff["movable_assets_json"])    if aff.get("movable_assets_json")    else None,
                    "immovable_json":json.dumps(aff["immovable_assets_json"])  if aff.get("immovable_assets_json")  else None,
                    "liab_json":     json.dumps(aff["liabilities_json"])       if aff.get("liabilities_json")       else None,
                    "crim_json":     json.dumps(aff["criminal_cases_detail_json"]) if aff.get("criminal_cases_detail_json") else None,
                    "itr_json":      json.dumps(aff["itr_income_json"])        if aff.get("itr_income_json")        else None,
                    "education":     ls.get("education"),
                    "age":           ls.get("age"),
                    "parse_status":  parse_status,
                    "source_url":    aff.get("source_affidavit_url"),
                    "snapshot_path": aff.get("html_snapshot_path"),
                    "parse_error":   aff.get("parse_error"),
                })
            aff_upserted += 1

            # ── 2. candidate_master — update enrichable fields ─────────────
            if not dry_run:
                conn.execute(text("""
                    UPDATE candidate_master SET
                        net_worth_rs    = COALESCE(:net_worth, net_worth_rs),
                        self_profession = COALESCE(:profession, self_profession)
                    WHERE candidate_id = :cid
                """), {
                    "cid":        cid,
                    "net_worth":  net_worth,
                    "profession": aff.get("profession") or ls.get("profession"),
                })
            master_updated += 1

            # ── 3. candidate_party_history — election results ──────────────
            result = c.get("result_detail") or {}
            if not result:
                # Some files store results at top level
                result = {k: c[k] for k in (
                    "total_votes", "vote_share_pct", "rank",
                    "is_winner", "victory_margin_votes",
                ) if c.get(k) is not None}

            votes = result.get("total_votes") or result.get("votes_received")
            if votes and not dry_run:
                conn.execute(text("""
                    INSERT INTO candidate_party_history (
                        candidate_id, candidate_name, constituency,
                        election_year, party_id,
                        votes_received, vote_share, rank,
                        is_winner, result_position_label,
                        victory_margin_votes,
                        results_source, result_completeness_status
                    ) VALUES (
                        :cid, :name, :ac_id,
                        :yr, :party,
                        :votes, :share, :rank,
                        :winner, :pos_label,
                        :margin,
                        'myneta_json', 'complete'
                    )
                    ON CONFLICT DO NOTHING
                """), {
                    "cid":       cid,
                    "name":      c.get("name", ""),
                    "ac_id":     ac_id,
                    "yr":        election_year,
                    "party":     c.get("party", ""),
                    "votes":     votes,
                    "share":     result.get("vote_share_pct"),
                    "rank":      result.get("rank"),
                    "winner":    result.get("is_winner", False),
                    "pos_label": result.get("result_position_label"),
                    "margin":    result.get("victory_margin_votes"),
                })
                history_upserted += 1

    log.info("Done.")
    log.info("  candidate_affidavits  upserted : %d", aff_upserted)
    log.info("  candidate_master      updated  : %d", master_updated)
    log.info("  candidate_party_hist  inserted : %d", history_upserted)
    if dry_run:
        log.info("  (DRY RUN — no writes committed)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
