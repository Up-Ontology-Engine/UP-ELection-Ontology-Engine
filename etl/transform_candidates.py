"""
ETL: Candidates & Parties

Sources:
  data/data/affidavit_gorakhpur_all_candidates.json  → candidate_master
  data/data/neva_gorakhpur_mla_data.json             → enriches designation field
  data/data/text/affidavit_gorakhpur_urban_2022_*.txt → criminal_cases + assets via regex

Connector keys produced:
  candidate_id = slug of name + election year  e.g. "ADITYANATH_2022"
  party_id     = normalised party abbrev       e.g. "BJP"
  ac_id        = from AC_NAME_MAP              e.g. "GKP_322"

Run: python -m etl.transform_candidates
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import text
from etl.constants import normalise_party as _normalise_party

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parents[1] / "data" / "data"

ELECTION_MAP = {
    "UP Assembly Election - Jan-March 2022": "UP_ASM_2022",
    "UP Assembly Election 2022":             "UP_ASM_2022",
    "General Election 2024 (Lok Sabha)":     "LS_2024",
    "General Election 2024":                 "LS_2024",
}


def _make_candidate_id(name: str, election_year: int) -> str:
    slug = re.sub(r"[^A-Z0-9]", "_", name.strip().upper())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return f"{slug}_{election_year}"


def _parse_election_year(election_str: str) -> int:
    m = re.search(r"\b(20\d{2})\b", election_str)
    return int(m.group(1)) if m else 0


def _read_affidavit_json() -> list[dict]:
    path = DATA_DIR / "text" / "affidavit_gorakhpur_all_candidates.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    rows: list[dict] = []
    sections = [
        ("gorakhpur_urban_2022_assembly",  "GKP_322"),
        ("gorakhpur_rural_2022_assembly",  "GKP_323"),
        ("gorakhpur_2024_lok_sabha",       "GKP_LS64"),
    ]
    for key, ac_id in sections:
        section = data.get(key, {})
        election_str = section.get("election", "")
        year         = _parse_election_year(election_str)
        election_id  = ELECTION_MAP.get(election_str, f"UNKNOWN_{year}")

        for cand in section.get("key_candidates", []):
            name     = cand.get("name", "").strip()
            party_id = _normalise_party(cand.get("party", ""))
            rows.append({
                "candidate_id": _make_candidate_id(name, year),
                "name":         name,
                "party":        party_id,
                "ac_id":        ac_id,
                "election_year":year,
                "election_id":  election_id,
                "status":       cand.get("status", "Unknown"),
                "designation":  None,
                "is_incumbent": False,
                "is_primary_opp": False,
            })
    return rows


def _enrich_from_neva(rows: list[dict]) -> list[dict]:
    """Set designation + is_incumbent from neva MLA data."""
    path = DATA_DIR / "text" / "neva_gorakhpur_mla_data.json"
    if not path.exists():
        return rows

    with open(path, encoding="utf-8") as f:
        neva = json.load(f)

    mla_map: dict[str, str] = {}
    for key in ["gorakhpur_urban_mla", "gorakhpur_rural_mla"]:
        entry = neva.get(key, {})
        name  = entry.get("name", "").replace("Shri ", "").replace("Smt. ", "").strip()
        if name:
            mla_map[name.upper()] = entry.get("designation", "MLA")

    for row in rows:
        upper = row["name"].upper()
        # Partial name match
        matched = next((v for k, v in mla_map.items() if k in upper or upper in k), None)
        if matched:
            row["designation"]  = matched
            row["is_incumbent"] = True

    return rows


def load_candidate_master(engine: sa.Engine) -> int:
    rows = _read_affidavit_json()
    rows = _enrich_from_neva(rows)

    with engine.connect() as conn:
        for row in rows:
            conn.execute(
                text("""
                    INSERT INTO candidate_master
                        (candidate_id, name, party, ac_id, election_year,
                         is_incumbent, is_primary_opp)
                    VALUES
                        (:candidate_id, :name, :party, :ac_id, :election_year,
                         :is_incumbent, :is_primary_opp)
                    ON CONFLICT (candidate_id) DO UPDATE SET
                        party       = EXCLUDED.party,
                        is_incumbent = EXCLUDED.is_incumbent
                """),
                row,
            )
        conn.commit()

    logger.info("Upserted %d candidates into candidate_master", len(rows))
    return len(rows)


def compute_net_worth(engine: sa.Engine) -> int:
    """
    Backfill candidate_master.net_worth_rs = total_assets - total_liabilities
    for all candidates where it is not yet set.
    Returns number of rows updated.
    """
    with engine.connect() as conn:
        result = conn.execute(text("""
            UPDATE candidate_master cm
            SET net_worth_rs = ca.total_assets - ca.total_liabilities
            FROM candidate_affidavits ca
            WHERE ca.candidate_id = cm.candidate_id
              AND ca.total_assets IS NOT NULL
              AND ca.total_liabilities IS NOT NULL
              AND cm.net_worth_rs IS NULL
        """))
        conn.commit()
    updated = result.rowcount
    logger.info("compute_net_worth: updated %d rows", updated)
    return updated


def merge_affidavit_detail(engine: sa.Engine, rows: list[dict]) -> int:
    """
    Apply enriched affidavit fields (from MyNeta detail-page scrape) to
    candidate_affidavits, then refresh net_worth_rs on candidate_master.

    Each dict in `rows` must have at minimum: candidate_id.
    All other fields are optional — COALESCE keeps existing values when new value is None.

    Returns number of affidavit rows touched.
    """
    if not rows:
        return 0

    jsonb_fields = (
        "movable_assets_json", "immovable_assets_json", "liabilities_json",
        "criminal_case_details_json", "itr_income_json",
    )
    count = 0
    with engine.connect() as conn:
        for row in rows:
            cid = row.get("candidate_id")
            if not cid:
                continue

            params: dict = {"cid": cid}
            for f in jsonb_fields:
                v = row.get(f)
                params[f] = json.dumps(v, ensure_ascii=False) if v is not None else None

            params.update({
                "movable_assets_rs":    row.get("movable_assets_rs"),
                "immovable_assets_rs":  row.get("immovable_assets_rs"),
                "source_affidavit_url": row.get("source_affidavit_url"),
                "html_snapshot_path":   row.get("html_snapshot_path"),
                "parse_status":         row.get("parse_status", "scraped"),
                "parse_error":          row.get("parse_error"),
            })

            conn.execute(text("""
                UPDATE candidate_affidavits SET
                    movable_assets_rs          = COALESCE(:movable_assets_rs,    movable_assets_rs),
                    immovable_assets_rs        = COALESCE(:immovable_assets_rs,  immovable_assets_rs),
                    movable_assets_json        = COALESCE(CAST(:movable_assets_json   AS jsonb), movable_assets_json),
                    immovable_assets_json      = COALESCE(CAST(:immovable_assets_json AS jsonb), immovable_assets_json),
                    liabilities_json           = COALESCE(CAST(:liabilities_json      AS jsonb), liabilities_json),
                    criminal_case_details_json = COALESCE(CAST(:criminal_case_details_json AS jsonb),
                                                          criminal_case_details_json),
                    itr_income_json            = COALESCE(CAST(:itr_income_json AS jsonb), itr_income_json),
                    source_affidavit_url       = COALESCE(:source_affidavit_url, source_affidavit_url),
                    html_snapshot_path         = COALESCE(:html_snapshot_path,   html_snapshot_path),
                    parse_status               = :parse_status,
                    parse_error                = :parse_error,
                    scraped_at                 = NOW()
                WHERE candidate_id = :cid
            """), params)
            count += 1

        conn.commit()

    logger.info("merge_affidavit_detail: updated %d affidavit rows", count)
    compute_net_worth(engine)
    return count


def validate(engine: sa.Engine) -> None:
    with engine.connect() as conn:
        total     = conn.execute(text("SELECT COUNT(*) FROM candidate_master")).scalar()
        by_party  = conn.execute(text(
            "SELECT party, COUNT(*) FROM candidate_master GROUP BY party ORDER BY COUNT(*) DESC"
        )).fetchall()
        enriched  = conn.execute(text(
            "SELECT COUNT(*) FROM candidate_affidavits WHERE parse_status = 'scraped'"
        )).scalar()
        with_results = conn.execute(text(
            "SELECT COUNT(*) FROM candidate_party_history WHERE is_winner IS NOT NULL"
        )).scalar()
    logger.info(
        "[VALIDATE] %d candidates | %d affidavits enriched | %d result rows | by party: %s",
        total, enriched, with_results, {r[0]: r[1] for r in by_party},
    )


def run():
    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    load_candidate_master(engine)
    compute_net_worth(engine)
    validate(engine)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()
