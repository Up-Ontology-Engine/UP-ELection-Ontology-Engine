"""
Post-Form20 helper: expand gorakhpur_aliases.json from booth_master.

Once Form-20 data is loaded (via etl/parse_form20_xls.py or
ingestion/eci_booth_results.py), booth_master.polling_station_name
will have real station names for all 235 booths.

This script reads those names and adds them to geo_aliases so
the NLP geo-resolver can assign booth_ids to location mentions.

Run AFTER Form-20 data is loaded:
    python -m etl.expand_aliases
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

ALIAS_FILE = Path(__file__).parents[1] / "data" / "seeds" / "gorakhpur_aliases.json"
AC_ID = "GKP_322"


def _to_key_variants(name: str) -> list[str]:
    """Generate lookup variants from a raw polling station name."""
    clean = name.strip()
    variants = [clean]

    # Drop common suffixes
    for suffix in (
        " Primary School", " Junior High School", " Inter College",
        " Government School", " Govt School", " Govt.", "Praathmik Vidyalaya",
        " Parts", r"\(Part[s]?\s*\d+.*\)", r"\(Parts.*\)"
    ):
        trimmed = re.sub(suffix, "", clean, flags=re.IGNORECASE).strip()
        if trimmed and trimmed not in variants:
            variants.append(trimmed)

    # Strip trailing part numbers: "Madhopur (Parts 1,2,3)" → "Madhopur"
    m = re.match(r"^(.+?)\s*\(Parts?\s*[\d,\s]+\)$", clean, re.IGNORECASE)
    if m:
        core = m.group(1).strip()
        if core not in variants:
            variants.append(core)

    return [v for v in variants if len(v) >= 3]


def expand_aliases(engine: sa.Engine) -> int:
    with open(ALIAS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    aliases: dict = data.get("geo_aliases", {})
    localities: dict = data.get("localities", {})

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT booth_id, polling_station_name, locality_hint
            FROM booth_master
            WHERE ac_id = :ac_id
              AND booth_id NOT LIKE '%_TOTAL'
              AND polling_station_name IS NOT NULL
            ORDER BY booth_number
        """), {"ac_id": AC_ID}).mappings().fetchall()

    added = 0
    for row in rows:
        booth_id = row["booth_id"]
        entry = {"id": booth_id, "type": "booth"}

        for variant in _to_key_variants(row["polling_station_name"] or ""):
            if variant not in aliases:
                aliases[variant] = entry
                added += 1

        if row["locality_hint"] and row["locality_hint"] not in aliases:
            aliases[row["locality_hint"]] = entry
            added += 1

        # localities section: booth_id → [name1, name2, ...]
        if booth_id not in localities:
            names = [row["polling_station_name"]]
            if row["locality_hint"]:
                names.append(row["locality_hint"])
            localities[booth_id] = names

    data["geo_aliases"] = aliases
    data["localities"] = localities

    with open(ALIAS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info("Added %d alias entries from %d booth rows", added, len(rows))
    return added


def run() -> None:
    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    n = expand_aliases(engine)
    print(f"Expanded gorakhpur_aliases.json: +{n} entries.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()
