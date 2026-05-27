"""
ETL: Geocode Gorakhpur polling stations → lat/lon in booth_master.

Strategy (in priority order):
  1. Fuzzy match locality_hint / station name against known Gorakhpur landmarks
  2. Nominatim (OpenStreetMap) — politely rate-limited at 1 req/sec
  3. Centroid fallback with small random jitter (so booths spread on map)

Gorakhpur Urban bounding box: lat 26.70–26.82, lon 83.33–83.46

Run:
    python -m etl.geocode_booths               # all booths in GKP_322
    python -m etl.geocode_booths --ac-id all   # every AC
    python -m etl.geocode_booths --dry-run     # print only, no DB writes
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

AC_CENTROID: dict[str, tuple[float, float]] = {
    "GKP_322": (26.760, 83.375),
    "GKP_323": (26.740, 83.430),
    "GKP_320": (26.800, 83.270),
    "GKP_321": (26.840, 83.343),
    "GKP_324": (26.700, 83.443),
    "GKP_325": (26.610, 83.352),
    "GKP_326": (26.880, 83.520),
    "GKP_327": (26.770, 83.622),
    "GKP_328": (26.620, 83.542),
}

# Known precise coordinates for Gorakhpur Urban landmarks
KNOWN_LOCALITIES: dict[str, tuple[float, float]] = {
    "Golghar": (26.7616, 83.3731),
    "Civil Lines": (26.7630, 83.3690),
    "Railway Station": (26.7571, 83.3740),
    "BRD Medical": (26.7628, 83.3968),
    "Medical College": (26.7628, 83.3968),
    "Shahpur": (26.7540, 83.3650),
    "Mohaddipur": (26.7740, 83.3730),
    "Rustampur": (26.7680, 83.3820),
    "Chargawan": (26.7990, 83.3260),
    "Mirzapur": (26.7500, 83.3880),
    "Dhumanganj": (26.7700, 83.3820),
    "Ramgarh Tal": (26.7450, 83.3760),
    "Betiahata": (26.7650, 83.3800),
    "Shivpuri": (26.7550, 83.3750),
    "Basharatpur": (26.7600, 83.3620),
    "Humayunpur": (26.7690, 83.3550),
    "Alinagar": (26.7720, 83.3640),
    "Uska Bazar": (26.7800, 83.3900),
    "Madan Mohan": (26.7620, 83.3780),
    "Jungle Kauria": (26.6900, 83.4100),
    "Deoria Naka": (26.7540, 83.3640),
    "Taramandal": (26.7800, 83.3700),
    "Padrauna Road": (26.7750, 83.4100),
    "Gorakhnath": (26.7810, 83.3680),
    "Pipraich": (26.8400, 83.3430),
    "Sahjanwa": (26.7080, 83.4400),
    "Campierganj": (26.7990, 83.2750),
    "Bansgaon": (26.5490, 83.3590),
    "Belghat": (26.6210, 83.5420),
    "Gagaha": (26.7220, 83.4580),
}


def _fuzzy_known_match(name: str) -> Optional[tuple[float, float]]:
    try:
        from thefuzz import process as fuzz

        keys = list(KNOWN_LOCALITIES.keys())
        match, score = fuzz.extractOne(name, keys)
        if score >= 68:
            return KNOWN_LOCALITIES[match]
    except Exception:
        pass
    return None


def _nominatim_geocode(name: str) -> Optional[tuple[float, float]]:
    try:
        import requests

        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": f"{name}, Gorakhpur, Uttar Pradesh, India", "format": "json", "limit": 1},
            headers={"User-Agent": "GorakhpurPoliticalKG/0.1"},
            timeout=10,
        )
        resp.raise_for_status()
        hits = resp.json()
        if hits:
            lat, lon = float(hits[0]["lat"]), float(hits[0]["lon"])
            if 26.4 <= lat <= 27.1 and 83.0 <= lon <= 83.9:
                return (lat, lon)
    except Exception as exc:
        logger.debug("Nominatim failed for '%s': %s", name, exc)
    return None


def geocode_booths(engine: sa.Engine, ac_id: str = "GKP_322", dry_run: bool = False) -> int:
    ac_filter = "TRUE" if ac_id == "all" else "ac_id = :ac_id"
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text(f"""
            SELECT booth_id, ac_id, polling_station_name, locality_hint
            FROM booth_master
            WHERE {ac_filter}
              AND lat IS NULL
              AND booth_id NOT LIKE '%_TOTAL'
              AND polling_station_name IS NOT NULL
            ORDER BY ac_id, booth_number
        """),
                {} if ac_id == "all" else {"ac_id": ac_id},
            )
            .mappings()
            .fetchall()
        )

    logger.info("Geocoding %d booths (ac_id=%s)", len(rows), ac_id)
    geocoded = 0
    nominatim_calls = 0

    for row in rows:
        bid = row["booth_id"]
        hint = (row["locality_hint"] or "").strip()
        bname = (row["polling_station_name"] or "").split("(")[0].strip()
        centroid = AC_CENTROID.get(row["ac_id"], (26.760, 83.375))

        lat = lon = None

        # 1. Fuzzy match against known landmarks
        for search in filter(None, [hint, bname]):
            coords = _fuzzy_known_match(search)
            if coords:
                lat, lon = coords
                break

        # 2. Nominatim (rate-limited)
        if lat is None:
            for search in filter(None, [hint, bname]):
                if len(search) > 3:
                    coords = _nominatim_geocode(search)
                    nominatim_calls += 1
                    if coords:
                        lat, lon = coords
                        time.sleep(1.1)
                        break
                    time.sleep(1.1)

        # 3. Centroid + jitter
        if lat is None:
            import random

            rng = random.Random(hash(bid))
            lat = centroid[0] + rng.uniform(-0.022, 0.022)
            lon = centroid[1] + rng.uniform(-0.022, 0.022)

        if dry_run:
            logger.info("[DRY] %s → (%.4f, %.4f)", bid, lat, lon)
        else:
            with engine.connect() as conn:
                conn.execute(
                    text("""
                    UPDATE booth_master
                    SET lat = :lat, lon = :lon, geocoded_at = NOW()
                    WHERE booth_id = :bid
                """),
                    {"lat": lat, "lon": lon, "bid": bid},
                )
                conn.commit()

        geocoded += 1
        if geocoded % 50 == 0:
            logger.info("Progress: %d / %d", geocoded, len(rows))

    logger.info("Geocoded %d booths (Nominatim calls: %d)", geocoded, nominatim_calls)
    return geocoded


def run(ac_id: str = "GKP_322", dry_run: bool = False) -> None:
    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    n = geocode_booths(engine, ac_id=ac_id, dry_run=dry_run)
    print(f"Geocoded {n} booths.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--ac-id", default="GKP_322", help="AC ID or 'all'")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    run(args.ac_id, args.dry_run)
