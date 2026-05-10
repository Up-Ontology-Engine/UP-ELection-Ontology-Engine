"""
ETL: Geography — ac_master + booth_master

Sources:
  data/data/eci_electoral_roll_gorakhpur.json  → ac_master rows
  data/data/Convert to xcel sheet/electoral_roll.xlsx        → booth_master + voter demographics
  data/data/Convert to xcel sheet/electoral_roll (1).xlsx    → same, additional parts

Connector keys produced (MUST match all downstream scripts):
  ac_id    = "GKP_{ac_number}"           e.g. "GKP_322"
  booth_id = "GKP_{ac_number}_{part:03d}" e.g. "GKP_322_045"

Run: python -m etl.transform_geography
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import pandas as pd
import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parents[1] / "data" / "data"

AC_NUMBER = 322          # Gorakhpur Urban — pilot scope
AC_ID     = "GKP_322"
AC_NAME   = "Gorakhpur Urban"

# All 9 Gorakhpur ACs for ac_master (even if booth data is only for 322)
AC_REGISTRY = [
    {"ac_id": "GKP_320", "ac_number": 320, "ac_name": "Caimpiyarganj",  "ac_type": "rural"},
    {"ac_id": "GKP_321", "ac_number": 321, "ac_name": "Pipraich",       "ac_type": "rural"},
    {"ac_id": "GKP_322", "ac_number": 322, "ac_name": "Gorakhpur Urban","ac_type": "urban"},
    {"ac_id": "GKP_323", "ac_number": 323, "ac_name": "Gorakhpur Rural","ac_type": "rural"},
    {"ac_id": "GKP_324", "ac_number": 324, "ac_name": "Sahajanwa",      "ac_type": "rural"},
    {"ac_id": "GKP_325", "ac_number": 325, "ac_name": "Khajani",        "ac_type": "rural"},
    {"ac_id": "GKP_326", "ac_number": 326, "ac_name": "Chauri-Chaura",  "ac_type": "rural"},
    {"ac_id": "GKP_327", "ac_number": 327, "ac_name": "Bansgaon",       "ac_type": "rural"},
    {"ac_id": "GKP_328", "ac_number": 328, "ac_name": "Chillupar",      "ac_type": "rural"},
    # Lok Sabha seat — referenced by candidate data (Gorakhpur Parliamentary Constituency)
    {"ac_id": "GKP_LS64", "ac_number": 64, "ac_name": "Gorakhpur (LS)", "ac_type": "lok_sabha"},
]


def load_ac_master(engine: sa.Engine) -> int:
    """Insert all 9 Gorakhpur ACs into ac_master."""
    with engine.connect() as conn:
        for row in AC_REGISTRY:
            conn.execute(
                text("""
                    INSERT INTO ac_master (ac_id, ac_name, ac_type, district_id, district_name, state)
                    VALUES (:ac_id, :ac_name, :ac_type, 'GKP', 'Gorakhpur', 'Uttar Pradesh')
                    ON CONFLICT (ac_id) DO UPDATE
                      SET ac_name = EXCLUDED.ac_name,
                          ac_type = EXCLUDED.ac_type
                """),
                row,
            )
        conn.commit()
    logger.info("Upserted %d rows into ac_master", len(AC_REGISTRY))
    return len(AC_REGISTRY)


def _read_electoral_roll(path: Path) -> pd.DataFrame:
    """Read one electoral roll xlsx, keep only Part No + Gender + Age + Status."""
    df = pd.read_excel(path, engine="openpyxl", dtype=str)
    df.columns = [c.strip() for c in df.columns]

    # Standardise column names
    rename = {
        "Seq No.":            "seq_no",
        "Name":               "name",
        "Father/Husband Name":"father_name",
        "House No.":          "house_no",
        "Age":                "age",
        "Gender":             "gender",
        "Status":             "status",
        "EPIC No.":           "epic_no",
        "Part No.":           "part_no",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    required = {"part_no", "gender", "age", "status"}
    missing  = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns {missing} in {path.name}")

    df["part_no"] = pd.to_numeric(df["part_no"], errors="coerce")
    df["age"]     = pd.to_numeric(df["age"],     errors="coerce")
    df = df.dropna(subset=["part_no"])
    df["part_no"] = df["part_no"].astype(int)

    # Drop all PII columns — keep only aggregatable fields
    return df[["part_no", "gender", "age", "status"]].copy()


def _aggregate_booth_demographics(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-voter records to booth-level counts. Zero PII."""
    agg = (
        df.groupby("part_no")
        .apply(lambda g: pd.Series({
            "total_voters":   len(g),
            "male_voters":    (g["gender"].str.upper() == "M").sum(),
            "female_voters":  (g["gender"].str.upper() == "F").sum(),
            "other_voters":   (~g["gender"].str.upper().isin(["M", "F"])).sum(),
            "active_voters":  (g["status"].str.upper() == "A").sum(),
            "age_18_25":      ((g["age"] >= 18) & (g["age"] <= 25)).sum(),
            "age_26_40":      ((g["age"] >= 26) & (g["age"] <= 40)).sum(),
            "age_40_60":      ((g["age"] >= 41) & (g["age"] <= 60)).sum(),
            "age_60_plus":    (g["age"] > 60).sum(),
        }), include_groups=False)
        .reset_index()
    )
    agg["booth_id"] = agg["part_no"].apply(lambda p: f"GKP_{AC_NUMBER}_{p:03d}")
    agg["ac_id"]    = AC_ID
    return agg


def load_booth_master(engine: sa.Engine) -> int:
    """Build booth_master from electoral roll xlsx files."""
    roll_files = [
        DATA_DIR / "Convert to xcel sheet" / "electoral_roll.xlsx",
        DATA_DIR / "Convert to xcel sheet" / "electoral_roll (1).xlsx",
    ]

    frames = []
    for f in roll_files:
        if f.exists():
            try:
                frames.append(_read_electoral_roll(f))
                logger.info("Read %s", f.name)
            except Exception as e:
                logger.warning("Skipping %s: %s", f.name, e)

    if not frames:
        raise FileNotFoundError("No electoral roll xlsx files readable")

    df      = pd.concat(frames, ignore_index=True)
    booths  = _aggregate_booth_demographics(df)

    inserted = 0
    with engine.connect() as conn:
        for _, row in booths.iterrows():
            conn.execute(
                text("""
                    INSERT INTO booth_master
                        (booth_id, ac_id, booth_number, male_voters, female_voters,
                         other_voters, total_voters)
                    VALUES
                        (:booth_id, :ac_id, :part_no, :male_voters, :female_voters,
                         :other_voters, :total_voters)
                    ON CONFLICT (booth_id) DO UPDATE SET
                        male_voters   = EXCLUDED.male_voters,
                        female_voters = EXCLUDED.female_voters,
                        other_voters  = EXCLUDED.other_voters,
                        total_voters  = EXCLUDED.total_voters,
                        updated_at    = NOW()
                """),
                {
                    "booth_id":     row["booth_id"],
                    "ac_id":        row["ac_id"],
                    "part_no":      int(row["part_no"]),
                    "male_voters":  int(row["male_voters"]),
                    "female_voters":int(row["female_voters"]),
                    "other_voters": int(row["other_voters"]),
                    "total_voters": int(row["total_voters"]),
                },
            )
            inserted += 1
        conn.commit()

    logger.info("Upserted %d booth rows into booth_master (AC %s)", inserted, AC_ID)
    return inserted


def validate(engine: sa.Engine) -> None:
    with engine.connect() as conn:
        ac_count    = conn.execute(text("SELECT COUNT(*) FROM ac_master")).scalar()
        booth_count = conn.execute(text("SELECT COUNT(*) FROM booth_master WHERE ac_id = :ac"), {"ac": AC_ID}).scalar()
        total_v     = conn.execute(text("SELECT SUM(total_voters) FROM booth_master WHERE ac_id = :ac"), {"ac": AC_ID}).scalar()
    logger.info("[VALIDATE] ac_master: %d rows | booth_master GKP_322: %d booths | %d total voters",
                ac_count, booth_count, total_v or 0)


def run():
    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    load_ac_master(engine)
    load_booth_master(engine)
    validate(engine)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()
