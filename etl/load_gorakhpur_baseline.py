"""
Gorakhpur Baseline Loader
Loads governance, candidate, and panchayat data from the pre-fetched JSONs.
Steps:
  1. Normalise party names in booth_results
  2. Ensure ac_master has all 9 Gorakhpur ACs
  3. Load NeVA MLA data into candidate_master
  4. Load affidavit candidates into candidate_master
  5. Load eGramSwaraj block/panchayat data into panchayat_master
  6. Compute turnout_stats from booth_results

Run:
  python -m etl.load_gorakhpur_baseline
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path("data/data")
TEXT_DIR = DATA_DIR / "text"

# ──────────────────────────────────────────────────────────────────────────────
# 1. Party Name Normalisation
# ──────────────────────────────────────────────────────────────────────────────

PARTY_NORM = {
    "PARTY_AFFILIATION": None,        # Generic placeholder — drop
    "NAN": None,                       # Null — drop
    "BJP": "BJP",
    "BHARATIYA_JANATA_PAR": "BJP",
    "BHARTIYA_JANTA_PARTY": "BJP",
    "B.J.P": "BJP",
    "BHARATIYA JANATA PARTY": "BJP",
    "SP": "SP",
    "SAMAJWADI_PARTY": "SP",
    "SAMAJWADI PARTY": "SP",
    "BSP": "BSP",
    "B.S.P": "BSP",
    "BAHUJAN_SAMAJ_PARTY": "BSP",
    "BAHUJAN SAMAJ PARTY": "BSP",
    "INC": "INC",
    "INDIAN_NATIONAL_CONGRE": "INC",
    "INDIAN NATIONAL CONGRESS": "INC",
    "NOTA": "NOTA",
    "NONE OF THE ABOVE": "NOTA",
    "INDEPENDENT": "IND",
    "INDPENDENT": "IND",
    "AAP": "AAP",
    "AAM_AADAMI_PARTY": "AAP",
    "AAM AADAMI PARTY": "AAP",
}


def normalise_booth_results(conn):
    logger.info("Normalising party names in booth_results...")
    rows = conn.execute(text("SELECT DISTINCT party FROM booth_results")).fetchall()
    dirty = [r[0] for r in rows if r[0] not in set(PARTY_NORM.values()) - {None}]
    for raw in dirty:
        normalised = PARTY_NORM.get(raw)
        if normalised is None:
            conn.execute(text("DELETE FROM booth_results WHERE party = :p"), {"p": raw})
            logger.info(f"  Deleted rows with party='{raw}'")
        elif normalised != raw:
            conn.execute(text(
                "UPDATE booth_results SET party = :new WHERE party = :old"
            ), {"new": normalised, "old": raw})
            logger.info(f"  Renamed '{raw}' → '{normalised}'")
    conn.commit()
    logger.info("Party normalisation done.")


# ──────────────────────────────────────────────────────────────────────────────
# 2. Gorakhpur AC Master (ensure all 9 ACs exist)
# Schema: ac_id, ac_name, ac_type, district_id, district_name, state
# ──────────────────────────────────────────────────────────────────────────────

GORAKHPUR_ACS = [
    {"ac_id": "GKP_320", "ac_name": "Caimpiyarganj",   "ac_type": "Rural",  "district_name": "Gorakhpur"},
    {"ac_id": "GKP_321", "ac_name": "Pipraich",        "ac_type": "Rural",  "district_name": "Gorakhpur"},
    {"ac_id": "GKP_322", "ac_name": "Gorakhpur Urban", "ac_type": "Urban",  "district_name": "Gorakhpur"},
    {"ac_id": "GKP_323", "ac_name": "Gorakhpur Rural", "ac_type": "Rural",  "district_name": "Gorakhpur"},
    {"ac_id": "GKP_324", "ac_name": "Sahajanwa",       "ac_type": "Rural",  "district_name": "Gorakhpur"},
    {"ac_id": "GKP_325", "ac_name": "Khajani",         "ac_type": "Rural",  "district_name": "Gorakhpur"},
    {"ac_id": "GKP_326", "ac_name": "Chauri-Chaura",   "ac_type": "Rural",  "district_name": "Gorakhpur"},
    {"ac_id": "GKP_327", "ac_name": "Bansgaon",        "ac_type": "Rural",  "district_name": "Gorakhpur"},
    {"ac_id": "GKP_328", "ac_name": "Chillupar",       "ac_type": "Rural",  "district_name": "Gorakhpur"},
]


def load_ac_master(conn):
    logger.info("Loading ac_master for all 9 Gorakhpur ACs...")
    for ac in GORAKHPUR_ACS:
        conn.execute(text("""
            INSERT INTO ac_master (ac_id, ac_name, ac_type, district_name, state)
            VALUES (:ac_id, :ac_name, :ac_type, :district_name, 'Uttar Pradesh')
            ON CONFLICT (ac_id) DO UPDATE SET
                ac_name = EXCLUDED.ac_name,
                ac_type = EXCLUDED.ac_type,
                district_name = EXCLUDED.district_name
        """), ac)
    conn.commit()
    count = conn.execute(text("SELECT COUNT(*) FROM ac_master WHERE district_name='Gorakhpur'")).scalar()
    logger.info(f"  ac_master now has {count} Gorakhpur ACs.")


# ──────────────────────────────────────────────────────────────────────────────
# 3. NeVA MLA Data → candidate_master
# Schema: candidate_id, name, name_hi, party, ac_id, election_year, is_incumbent
# ──────────────────────────────────────────────────────────────────────────────

def load_neva_mla(conn):
    neva_path = TEXT_DIR / "neva_gorakhpur_mla_data.json"
    if not neva_path.exists():
        logger.warning("NeVA MLA file not found, skipping.")
        return
    data = json.loads(neva_path.read_text(encoding="utf-8"))
    mlas = []
    for key in ["gorakhpur_urban_mla", "gorakhpur_rural_mla"]:
        mla = data.get(key)
        if not mla:
            continue
        m = re.search(r'AC (\d+)', mla.get("constituency", ""))
        ac_num = int(m.group(1)) if m else None
        if not ac_num:
            continue
        ac_id = f"GKP_{ac_num}"
        party_raw = mla.get("party", "")
        party = "BJP" if "bharatiya janata" in party_raw.lower() else party_raw[:20].upper()
        name = mla.get("name", "").strip()
        mlas.append({
            "candidate_id": f"CAND_{ac_id}_MLA_2022",
            "ac_id": ac_id,
            "name": name,
            "party": party,
            "election_year": 2022,
            "is_incumbent": True,
        })

    for m in mlas:
        conn.execute(text("""
            INSERT INTO candidate_master
                (candidate_id, ac_id, name, party, election_year, is_incumbent)
            VALUES
                (:candidate_id, :ac_id, :name, :party, :election_year, :is_incumbent)
            ON CONFLICT (candidate_id) DO UPDATE SET
                name = EXCLUDED.name,
                party = EXCLUDED.party,
                is_incumbent = EXCLUDED.is_incumbent
        """), m)
    conn.commit()
    logger.info(f"  Loaded {len(mlas)} MLA records from NeVA data.")


# ──────────────────────────────────────────────────────────────────────────────
# 4. Affidavit JSON → candidate_master
# ──────────────────────────────────────────────────────────────────────────────

PARTY_SHORT = {
    "bharatiya janata party": "BJP", "bjp": "BJP",
    "samajwadi party": "SP",
    "bahujan samaj party": "BSP",
    "indian national congress": "INC",
    "azad samaj party": "ASP",
    "aam aadmi party": "AAP",
    "peace party": "PEACE",
    "independent": "IND",
}


def _short_party(raw: str) -> str:
    low = raw.lower()
    for k, v in PARTY_SHORT.items():
        if k in low:
            return v
    return re.sub(r"[^A-Z0-9]", "", raw.upper())[:20]


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:20]


def _make_cand_id(ac_id: str, name: str, year: int) -> str:
    return f"{ac_id}_{_slug(name)}_{year}"[:40]


def load_affidavits(conn):
    path = TEXT_DIR / "affidavit_gorakhpur_all_candidates.json"
    if not path.exists():
        logger.warning("Affidavit JSON not found, skipping.")
        return
    data = json.loads(path.read_text(encoding="utf-8"))

    AC_KEY_MAP = {
        "gorakhpur_urban_2022_assembly": 322,
        "gorakhpur_rural_2022_assembly": 323,
    }
    total = 0
    for key, ac_num in AC_KEY_MAP.items():
        block = data.get(key, {})
        ac_id = f"GKP_{ac_num}"
        for cand in block.get("key_candidates", []):
            name = cand.get("name", "").strip()
            party = _short_party(cand.get("party", "IND"))
            cand_id = _make_cand_id(ac_id, name, 2022)
            conn.execute(text("""
                INSERT INTO candidate_master
                    (candidate_id, ac_id, name, party, election_year, is_incumbent)
                VALUES
                    (:candidate_id, :ac_id, :name, :party, :election_year, FALSE)
                ON CONFLICT (candidate_id) DO NOTHING
            """), {
                "candidate_id": cand_id,
                "ac_id": ac_id,
                "name": name,
                "party": party,
                "election_year": 2022,
            })
            total += 1

    conn.commit()
    logger.info(f"  Loaded {total} candidates from affidavit JSON.")


# ──────────────────────────────────────────────────────────────────────────────
# 5. eGramSwaraj → panchayat_master
# Schema: panchayat_id, gp_name, block_name, district_id
# ──────────────────────────────────────────────────────────────────────────────

BLOCK_TO_AC = {
    "Khorabar": "GKP_322", "Sardarnagar": "GKP_322",
    "Pipraich": "GKP_321", "Piprauli": "GKP_321",
    "Campierganj": "GKP_320", "Bharohiya": "GKP_320",
    "Brahmpur": "GKP_323", "Chargawan": "GKP_323", "Gagaha": "GKP_323",
    "Sahjanawa": "GKP_324", "Gola": "GKP_324",
    "Khajni": "GKP_325", "Bhathat": "GKP_325", "Kauri Ram": "GKP_325",
    "Uruwa": "GKP_326",
    "Bansgaon": "GKP_327", "Barhalganj": "GKP_327", "Pali": "GKP_327",
    "Belghat": "GKP_328", "Jangal Kaudia": "GKP_328",
}


def load_egramswaraj(conn):
    path = TEXT_DIR / "egramswaraj_gorakhpur_panchayat_data.json"
    if not path.exists():
        logger.warning("eGramSwaraj JSON not found, skipping.")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    block_gps = data.get("block_wise_gram_panchayats", {})

    total = 0
    for block, gp_count in block_gps.items():
        panchayat_id = f"PAN_{_slug(block)}"
        conn.execute(text("""
            INSERT INTO panchayat_master (panchayat_id, gp_name, block_name, district_id)
            VALUES (:panchayat_id, :gp_name, :block_name, 'DIST_GKP')
            ON CONFLICT (panchayat_id) DO UPDATE SET
                gp_name = EXCLUDED.gp_name,
                block_name = EXCLUDED.block_name
        """), {
            "panchayat_id": panchayat_id,
            "gp_name": f"{block} Block ({gp_count} GPs)",
            "block_name": block,
        })
        total += 1

    conn.commit()
    logger.info(f"  Loaded {total} block-level panchayat records from eGramSwaraj.")


# ──────────────────────────────────────────────────────────────────────────────
# 6. Compute turnout_stats from booth_results
# Schema: booth_id, election_year, total_voters, total_votes, turnout_percent
# ──────────────────────────────────────────────────────────────────────────────

def compute_turnout_stats(conn):
    logger.info("Computing turnout_stats from booth_results...")
    conn.execute(text("""
        INSERT INTO turnout_stats (booth_id, election_year, total_votes)
        SELECT
            booth_id,
            election_year,
            SUM(votes) as total_votes
        FROM booth_results
        GROUP BY booth_id, election_year
        ON CONFLICT DO NOTHING
    """))
    conn.commit()
    r = conn.execute(text("SELECT COUNT(*) FROM turnout_stats")).scalar()
    logger.info(f"  turnout_stats now has {r} rows.")


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def run():
    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    with engine.connect() as conn:
        load_ac_master(conn)
        normalise_booth_results(conn)
        load_neva_mla(conn)
        load_affidavits(conn)
        load_egramswaraj(conn)
        compute_turnout_stats(conn)
    logger.info("✅ Gorakhpur Baseline Loader complete.")


if __name__ == "__main__":
    run()
