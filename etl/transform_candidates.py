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


def validate(engine: sa.Engine) -> None:
    with engine.connect() as conn:
        total     = conn.execute(text("SELECT COUNT(*) FROM candidate_master")).scalar()
        by_party  = conn.execute(text(
            "SELECT party, COUNT(*) FROM candidate_master GROUP BY party ORDER BY COUNT(*) DESC"
        )).fetchall()
    logger.info("[VALIDATE] %d total candidates | by party: %s", total, dict(by_party))


def run():
    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    load_candidate_master(engine)
    validate(engine)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()
