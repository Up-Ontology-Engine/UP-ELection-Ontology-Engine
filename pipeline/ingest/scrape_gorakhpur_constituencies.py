"""
Full pipeline: discover MyNeta constituency_ids → scrape → JSON → Postgres

Targets all 8 Gorakhpur-region ACs that currently have no constituency_id:
  GKP_320  Campierganj
  GKP_321  Pipraich
  GKP_323  Gorakhpur Rural
  GKP_324  Sahajanwa
  GKP_325  Khajani
  GKP_326  Chauri-Chaura
  GKP_327  Bansgaon
  GKP_328  Chillupar

Steps:
  1. Fetch the MyNeta UP-2022 index page and discover constituency_id for each AC name
  2. Scrape list + affidavit detail + expense (3 passes) per constituency
  3. Write data/Myneta/myneta_<ac_id>_2022.json
  4. Ingest all new JSON files into Postgres (candidate_master + candidate_affidavits)

Run:
  python pipeline/ingest/scrape_gorakhpur_constituencies.py
  python pipeline/ingest/scrape_gorakhpur_constituencies.py --no-ingest   # skip Postgres step
  python pipeline/ingest/scrape_gorakhpur_constituencies.py --dry-run      # discover IDs only
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).parents[2]
DATA_DIR = ROOT / "data" / "Myneta"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Target ACs (those without a confirmed constituency_id) ────────────────────
TARGETS = [
    # ac_number, ac_id,      ac_name,           election_folder
    (320, "GKP_320", "Caimpiyarganj",   "uttarpradesh2022"),
    (321, "GKP_321", "Pipraich",       "uttarpradesh2022"),
    (323, "GKP_323", "Gorakhpur Rural","uttarpradesh2022"),
    (324, "GKP_324", "Sahajanwa",      "uttarpradesh2022"),
    (325, "GKP_325", "Khajani",        "uttarpradesh2022"),
    (326, "GKP_326", "Chauri-Chaura",  "uttarpradesh2022"),
    (327, "GKP_327", "Bansgaon",       "uttarpradesh2022"),
    (328, "GKP_328", "Chillupar",      "uttarpradesh2022"),
]

ELECTION_YEAR = 2022
POSTGRES_URL  = os.environ.get(
    "POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/gorakhpur_db"
)

# Add repo root to path so we can import existing scraper helpers
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "pipeline" / "ingest"))

from myneta_candidates import (
    _normalise_party, _slugify,
    scrape_constituency_list, scrape_affidavit_detail, scrape_expense_page,
)

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    raise ImportError("pip install requests beautifulsoup4")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ── Step 1: discover constituency IDs from MyNeta index ──────────────────────

def _normalise_name(n: str) -> str:
    """Lowercase, strip punctuation for fuzzy matching."""
    return re.sub(r"[^a-z0-9]", "", n.lower())


def discover_constituency_ids(election_folder: str) -> dict[str, int]:
    """
    Fetch the MyNeta state index page and return {normalised_name: constituency_id}.
    """
    url = f"https://www.myneta.info/{election_folder}/"
    log.info("Fetching constituency list from %s …", url)
    time.sleep(1)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        log.error("Failed to fetch index: %s", e)
        return {}

    soup = BeautifulSoup(resp.text, "html.parser")
    mapping: dict[str, int] = {}

    for a in soup.find_all("a", href=True):
        href = str(a["href"])
        m = re.search(r"constituency_id=(\d+)", href)
        if m:
            name = a.get_text(strip=True)
            if name:
                mapping[_normalise_name(name)] = int(m.group(1))

    log.info("Discovered %d constituencies on index page", len(mapping))
    return mapping


def match_id(ac_name: str, mapping: dict[str, int]) -> int | None:
    """Fuzzy-match our AC name against the discovered names."""
    key = _normalise_name(ac_name)
    if key in mapping:
        return mapping[key]
    # Try prefix / substring
    for k, v in mapping.items():
        if key in k or k in key:
            return v
    return None


# ── Step 2: scrape one constituency (all 3 passes) ───────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def scrape_one(ac_id: str, ac_name: str, election_folder: str,
               constituency_id: int) -> dict:
    """Scrape list + detail + expense for one constituency, return JSON dict."""
    log.info("─── %s (%s) constituency_id=%d", ac_id, ac_name, constituency_id)

    candidates_raw = scrape_constituency_list(constituency_id, election_folder)
    log.info("  list pass: %d candidates", len(candidates_raw))

    records = []
    for c in candidates_raw:
        rec = {
            "candidate_id":       _slugify(c["name"], ELECTION_YEAR)[:40],
            "name":               c["name"],
            "party":              _normalise_party(c.get("party_raw", "")),
            "party_raw":          c.get("party_raw"),
            "ac_id":              ac_id,
            "ac_name":            ac_name,
            "election_year":      ELECTION_YEAR,
            "source_candidate_id": c.get("source_candidate_id"),
            "detail_url":         c.get("detail_url"),
            "list_summary": {
                "education":      c.get("education"),
                "age":            c.get("age"),
                "criminal_cases": c.get("criminal_cases"),
                "total_assets":   c.get("total_assets"),
                "liabilities":    c.get("liabilities"),
            },
            "affidavit_detail": {},
            "expense": {},
        }

        src = c.get("source_candidate_id")
        if src:
            log.debug("    detail %s (candidate_id=%d)", c["name"], src)
            rec["affidavit_detail"] = scrape_affidavit_detail(int(src), election_folder)
            time.sleep(0.4)
            rec["expense"] = scrape_expense_page(int(src), election_folder)
            time.sleep(0.3)

        records.append(rec)

    return {
        "ac_id":            ac_id,
        "ac_name":          ac_name,
        "election_year":    ELECTION_YEAR,
        "election_folder":  election_folder,
        "constituency_id":  constituency_id,
        "source":           "myneta",
        "passes":           ["list", "detail", "expense"],
        "scraped_at":       _now_iso(),
        "candidate_count":  len(records),
        "candidates":       records,
    }


# ── Step 3: ingest JSON files into Postgres ───────────────────────────────────

def ingest_json_file(path: Path, conn) -> tuple[int, int]:
    """Upsert one JSON file. Returns (aff_count, master_count)."""
    from sqlalchemy import text

    data = json.loads(path.read_text(encoding="utf-8"))
    cands = data.get("candidates", [])
    aff_done = master_done = 0

    for c in cands:
        cid = (c.get("candidate_id") or "").strip()[:40]
        if not cid:
            continue

        aff  = c.get("affidavit_detail") or {}
        ls   = c.get("list_summary") or {}
        ac_id        = c.get("ac_id", "")
        election_year = c.get("election_year") or 0

        movable_rs   = aff.get("movable_assets_rs")
        immovable_rs = aff.get("immovable_assets_rs")
        net_worth    = ((movable_rs or 0) + (immovable_rs or 0)) or ls.get("total_assets")
        parse_status = "scraped" if (aff.get("itr_income_json") or aff.get("movable_assets_json")) else (aff.get("parse_status") or "list_only")

        # 0. ensure candidate_master row
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
            ON CONFLICT (candidate_id) DO UPDATE SET
                net_worth_rs    = COALESCE(EXCLUDED.net_worth_rs, candidate_master.net_worth_rs),
                self_profession = COALESCE(EXCLUDED.self_profession, candidate_master.self_profession)
        """), {
            "cid":        cid,
            "name":       c.get("name", ""),
            "party":      c.get("party", "IND"),
            "ac_id":      ac_id,
            "yr":         election_year,
            "net_worth":  net_worth,
            "profession": aff.get("profession"),
            "src_id":     str(c.get("source_candidate_id") or ""),
        })
        master_done += 1

        # 1. candidate_affidavits upsert
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
                movable_assets_rs          = COALESCE(EXCLUDED.movable_assets_rs,          candidate_affidavits.movable_assets_rs),
                immovable_assets_rs        = COALESCE(EXCLUDED.immovable_assets_rs,        candidate_affidavits.immovable_assets_rs),
                movable_assets_json        = COALESCE(EXCLUDED.movable_assets_json,        candidate_affidavits.movable_assets_json),
                immovable_assets_json      = COALESCE(EXCLUDED.immovable_assets_json,      candidate_affidavits.immovable_assets_json),
                liabilities_json           = COALESCE(EXCLUDED.liabilities_json,           candidate_affidavits.liabilities_json),
                criminal_case_details_json = COALESCE(EXCLUDED.criminal_case_details_json, candidate_affidavits.criminal_case_details_json),
                itr_income_json            = COALESCE(EXCLUDED.itr_income_json,            candidate_affidavits.itr_income_json),
                education                  = COALESCE(EXCLUDED.education,                  candidate_affidavits.education),
                age                        = COALESCE(EXCLUDED.age,                        candidate_affidavits.age),
                parse_status               = EXCLUDED.parse_status,
                source_affidavit_url       = COALESCE(EXCLUDED.source_affidavit_url,       candidate_affidavits.source_affidavit_url),
                html_snapshot_path         = COALESCE(EXCLUDED.html_snapshot_path,         candidate_affidavits.html_snapshot_path),
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
            "movable_json":  json.dumps(aff["movable_assets_json"])       if aff.get("movable_assets_json")       else None,
            "immovable_json":json.dumps(aff["immovable_assets_json"])     if aff.get("immovable_assets_json")     else None,
            "liab_json":     json.dumps(aff["liabilities_json"])          if aff.get("liabilities_json")          else None,
            "crim_json":     json.dumps(aff["criminal_cases_detail_json"]) if aff.get("criminal_cases_detail_json") else None,
            "itr_json":      json.dumps(aff["itr_income_json"])           if aff.get("itr_income_json")           else None,
            "education":     ls.get("education"),
            "age":           ls.get("age"),
            "parse_status":  parse_status,
            "source_url":    aff.get("source_affidavit_url"),
            "snapshot_path": aff.get("html_snapshot_path"),
            "parse_error":   aff.get("parse_error"),
        })
        aff_done += 1

    return aff_done, master_done


def run_ingest(json_paths: list[Path]) -> None:
    import sqlalchemy as sa

    engine = sa.create_engine(POSTGRES_URL, pool_pre_ping=True)
    total_aff = total_master = 0
    with engine.begin() as conn:
        for p in json_paths:
            a, m = ingest_json_file(p, conn)
            log.info("  ingested %-40s → %d affidavits, %d master rows", p.name, a, m)
            total_aff    += a
            total_master += m
    log.info("Postgres totals — affidavits: %d  master: %d", total_aff, total_master)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",   action="store_true", help="Discover IDs only, no scrape")
    parser.add_argument("--no-ingest", action="store_true", help="Skip Postgres ingest step")
    parser.add_argument("--ac",        type=int, nargs="+",  help="Restrict to these AC numbers")
    args = parser.parse_args()

    targets = TARGETS
    if args.ac:
        targets = [t for t in targets if t[0] in args.ac]
    if not targets:
        log.error("No targets selected")
        sys.exit(1)

    # Step 1 — discover IDs
    election_folder = targets[0][3]
    id_map = discover_constituency_ids(election_folder)
    if not id_map:
        log.error("Could not fetch constituency index — aborting")
        sys.exit(1)

    resolved: list[tuple[str, str, str, int]] = []
    for ac_num, ac_id, ac_name, folder in targets:
        cid = match_id(ac_name, id_map)
        if cid:
            log.info("  ✓ %-30s → constituency_id=%d", ac_name, cid)
            resolved.append((ac_id, ac_name, folder, cid))
        else:
            log.warning("  ✗ %-30s → NOT FOUND in index", ac_name)

    if args.dry_run:
        log.info("Dry-run: stopping after ID discovery")
        return

    if not resolved:
        log.error("No IDs resolved — check constituency name spellings")
        sys.exit(1)

    # Step 2 — scrape
    written_paths: list[Path] = []
    for ac_id, ac_name, folder, constituency_id in resolved:
        out_path = DATA_DIR / f"myneta_{ac_id}_2022.json"

        data = scrape_one(ac_id, ac_name, folder, constituency_id)

        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("  Wrote %s (%d candidates)", out_path.name, data["candidate_count"])
        written_paths.append(out_path)

        time.sleep(0.5)  # breathe between constituencies

    log.info("Scraping complete. %d JSON files written.", len(written_paths))

    # Step 3 — ingest
    if args.no_ingest:
        log.info("--no-ingest: skipping Postgres step")
        return

    log.info("Ingesting into Postgres …")
    run_ingest(written_paths)
    log.info("All done.")


if __name__ == "__main__":
    main()
