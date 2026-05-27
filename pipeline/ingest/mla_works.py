"""
Scraper: MLA Work Done — Questions, Bills, Attendance from UP Legislature

Sources:
  1. NeVA (National e-Vidhan Application): neva.gov.in/UP
     - Questions raised by MLA in assembly
     - Bills introduced
     - Attendance record
  2. UP Vidhan Sabha: vidhan-sabha.up.gov.in
     - MLA profile + work done
  3. MyNeta work profile (if available)

What this produces:
  - New table: mla_work (candidate_id, work_type, description, session, date)
  - Updates candidate_master: questions_count, bills_count, attendance_pct

Key MLAs for Gorakhpur:
  AC 322 (Urban): Yogi Adityanath (BJP) — Chief Minister
  AC 323 (Rural): Bipin Singh (BJP)
  AC 320-328: All BJP winners from 2022

Run: python -m ingestion.mla_works
"""

from __future__ import annotations

import logging
import os
import re
import time

import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    raise ImportError("Run: pip install requests beautifulsoup4")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

# UP Vidhan Sabha 18th assembly (2022-2027)
VIDHAN_SABHA_BASE = "https://vidhan-sabha.up.gov.in"
NEVA_BASE = "https://neva.gov.in"

# Known Gorakhpur MLAs (from neva_gorakhpur_mla_data.json)
GORAKHPUR_MLAS = [
    {"ac_id": "GKP_322", "name": "Yogi Adityanath", "ac_no": 322},
    {"ac_id": "GKP_323", "name": "Bipin Singh", "ac_no": 323},
]


def ensure_mla_work_table(engine: sa.Engine) -> None:
    with engine.connect() as conn:
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS mla_work (
                id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                candidate_id    VARCHAR(40),
                ac_id           VARCHAR(30),
                work_type       VARCHAR(50),   -- questions | bills | development | attendance
                title           TEXT,
                description     TEXT,
                session_year    VARCHAR(10),
                work_date       DATE,
                source_url      TEXT,
                created_at      TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        )
        # Add work columns to candidate_master if not exist
        for col in [
            ("questions_count", "INTEGER DEFAULT 0"),
            ("bills_count", "INTEGER DEFAULT 0"),
            ("attendance_pct", "FLOAT DEFAULT 0"),
            ("dev_works_count", "INTEGER DEFAULT 0"),
        ]:
            try:
                conn.execute(
                    text(f"ALTER TABLE candidate_master ADD COLUMN IF NOT EXISTS {col[0]} {col[1]}")
                )
            except Exception:
                pass
        conn.commit()


def scrape_vidhan_sabha_mla(mla_name: str, ac_no: int) -> dict:
    """
    Scrape UP Vidhan Sabha member profile.
    Returns {questions_count, bills_count, attendance_pct, work_items[]}
    """
    result = {"questions": [], "bills": [], "attendance_pct": 0, "work_items": []}

    # Try Vidhan Sabha member search
    search_url = f"{VIDHAN_SABHA_BASE}/en/member/search"
    try:
        resp = requests.post(
            search_url,
            data={"name": mla_name, "constituency": str(ac_no)},
            headers=HEADERS,
            timeout=20,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Parse questions
        for item in soup.find_all(class_=re.compile(r"question|starred|unstarred", re.I)):
            title = item.get_text(strip=True)
            if title and len(title) > 10:
                result["questions"].append(title[:200])

        # Parse attendance
        att_elem = soup.find(string=re.compile(r"attendance|present", re.I))
        if att_elem:
            pct = re.search(r"(\d+\.?\d*)\s*%", att_elem)
            if pct:
                result["attendance_pct"] = float(pct.group(1))

    except Exception as e:
        logger.debug("Vidhan Sabha scrape failed for %s: %s", mla_name, e)

    # Try NeVA work profile
    neva_url = f"{NEVA_BASE}/en/member/{mla_name.lower().replace(' ', '-')}"
    try:
        resp = requests.get(neva_url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for row in soup.find_all("tr"):
                cells = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cells) >= 2:
                    result["work_items"].append(
                        {
                            "type": "work",
                            "title": cells[0][:100],
                            "desc": cells[1][:300] if len(cells) > 1 else "",
                        }
                    )
    except Exception as e:
        logger.debug("NeVA scrape failed for %s: %s", mla_name, e)

    return result


def load_mla_work(mla: dict, work: dict, engine: sa.Engine) -> None:
    cid = re.sub(r"[^A-Z0-9]+", "_", mla["name"].upper()) + "_2022"
    ac_id = mla["ac_id"]

    with engine.connect() as conn:
        # Insert work items
        for item in work.get("questions", []):
            conn.execute(
                text("""
                INSERT INTO mla_work (candidate_id, ac_id, work_type, title, session_year)
                VALUES (:cid, :ac, 'question', :title, '2022-2027')
                ON CONFLICT DO NOTHING
            """),
                {"cid": cid, "ac": ac_id, "title": item[:200]},
            )

        for item in work.get("work_items", []):
            conn.execute(
                text("""
                INSERT INTO mla_work
                    (candidate_id, ac_id, work_type, title, description, session_year)
                VALUES (:cid, :ac, :wtype, :title, :desc, '2022-2027')
                ON CONFLICT DO NOTHING
            """),
                {
                    "cid": cid,
                    "ac": ac_id,
                    "wtype": item.get("type", "development"),
                    "title": item.get("title", "")[:200],
                    "desc": item.get("desc", "")[:500],
                },
            )

        # Update candidate_master summary
        conn.execute(
            text("""
            UPDATE candidate_master SET
                questions_count = :qcount,
                attendance_pct  = :att
            WHERE candidate_id = :cid
        """),
            {
                "cid": cid,
                "qcount": len(work.get("questions", [])),
                "att": work.get("attendance_pct", 0),
            },
        )

        conn.commit()


def build_static_work_profile(engine: sa.Engine) -> None:
    """
    For Yogi Adityanath — Chief Minister — add known public work data.
    This is sourced from public records and news since CM doesn't participate
    in regular MLA question sessions.
    """
    cid = "YOGI_ADITYANATH_2022"
    known_works = [
        {
            "type": "development",
            "title": "Gorakhpur AIIMS established",
            "desc": "Medical college and AIIMS inaugurated in Gorakhpur during CM tenure",
        },
        {
            "type": "development",
            "title": "Gorakhpur Fertilizer Plant revived",
            "desc": "Hindustan Urvarak & Rasayan Limited plant restarted after decades",
        },
        {
            "type": "development",
            "title": "Gorakhpur Industrial Corridor",
            "desc": "Industrial corridor development for employment generation",
        },
        {
            "type": "development",
            "title": "UP Expressway connectivity",
            "desc": "Purvanchal Expressway operational, connecting Gorakhpur to Lucknow",
        },
        {
            "type": "development",
            "title": "Gorakhpur Link Expressway",
            "desc": "Link Expressway connecting Gorakhpur to Purvanchal Expressway",
        },
        {
            "type": "scheme",
            "title": "PMAY beneficiaries in Gorakhpur",
            "desc": "PM Awas Yojana housing scheme implementation in constituency",
        },
        {
            "type": "scheme",
            "title": "Jal Jeevan Mission",
            "desc": "Tap water connections to rural households in Gorakhpur",
        },
    ]

    with engine.connect() as conn:
        for w in known_works:
            conn.execute(
                text("""
                INSERT INTO mla_work
                    (candidate_id, ac_id, work_type, title, description, session_year)
                VALUES (:cid, 'GKP_322', :wtype, :title, :desc, '2022-2027')
                ON CONFLICT DO NOTHING
            """),
                {"cid": cid, "wtype": w["type"], "title": w["title"], "desc": w["desc"]},
            )

        conn.execute(
            text("""
            UPDATE candidate_master
            SET dev_works_count = :n
            WHERE candidate_id = :cid
        """),
            {"cid": cid, "n": len(known_works)},
        )
        conn.commit()

    logger.info("Loaded %d static work items for Yogi Adityanath", len(known_works))


def run():
    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    ensure_mla_work_table(engine)

    for mla in GORAKHPUR_MLAS:
        logger.info("Scraping work for: %s (%s)", mla["name"], mla["ac_id"])
        work = scrape_vidhan_sabha_mla(mla["name"], mla["ac_no"])
        load_mla_work(mla, work, engine)
        time.sleep(1.0)

    # Load static profile for CM
    build_static_work_profile(engine)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()
