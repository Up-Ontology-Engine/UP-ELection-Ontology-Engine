"""
ETL: PCA Census → village-level demographics → booth enrichment

Source:
  data/processed/text/PCA_CDB_0957_F_Census.xls   (3,383 rows × 96 columns)
  Sheet: EB-0957

Key columns used:
  Name, Level (VILLAGE/CD BLOCK), Total_Population_*, SC_*, ST_*,
  Literates_*, Worker_*, Non_Working_*

Approach:
  1. Filter rows where Level == "VILLAGE" and District == "Gorakhpur"
  2. Fuzzy-match village names → booth_id via gorakhpur_aliases.json
  3. Aggregate matched villages per booth_id
  4. Update booth_master with demographic enrichment

Note: Village → booth mapping requires gorakhpur_aliases.json to be populated.
      Unmatched villages are written to data/seeds/unmatched_villages.json for review.

Run: python -m etl.transform_census
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

DATA_DIR  = Path(__file__).parents[1] / "data" / "data"
SEEDS_DIR = Path(__file__).parents[1] / "data" / "seeds"


# Subset of 96 columns we care about (mapped to our output names)
COLUMN_MAP = {
    "Name":                              "village_name",
    "Level":                             "level",
    "District_Name":                     "district_name",
    "No of Households":                  "household_count",
    "Total Population Person":           "total_population",
    "Total Population Male":             "male_pop",
    "Total Population Female":           "female_pop",
    "Population in the age group 0-6 Person": "pop_0_6",
    "Scheduled Castes population Person":"sc_population",
    "Scheduled Tribes population Person":"st_population",
    "Literates Population Person":       "literate_count",
    "Illiterate Persons":                "illiterate_count",
    "Total Worker Population Person":    "total_workers",
    "Main Cultivator Population Person": "main_cultivators",
    "Main Agricultural Labourers Population Person": "agri_labourers",
    "Main Other Workers Population Person": "other_workers",
    "Non Working Population Person":     "non_workers",
}


def _load_aliases() -> dict[str, str]:
    """
    Load village name → booth_id reverse map from gorakhpur_aliases.json.
    Reads from 'localities' key: { "GKP_322_045": ["rustampur", "रुस्तमपुर"] }
    """
    alias_path = SEEDS_DIR / "gorakhpur_aliases.json"
    if not alias_path.exists():
        logger.warning("gorakhpur_aliases.json not found — no village→booth mapping possible")
        return {}
    with open(alias_path, encoding="utf-8") as f:
        data = json.load(f)

    reverse: dict[str, str] = {}
    localities = data.get("localities", {})
    for booth_id, aliases in localities.items():
        if booth_id.startswith("_"):   # skip comment keys
            continue
        if isinstance(aliases, list):
            for alias in aliases:
                reverse[alias.lower().strip()] = booth_id
        elif isinstance(aliases, str):
            reverse[aliases.lower().strip()] = booth_id
    return reverse


def load_census_to_booth(engine: sa.Engine) -> tuple[int, int]:
    """
    Returns (matched_count, unmatched_count).
    """
    try:
        import xlrd
    except ImportError:
        raise ImportError("Run: python -m pip install xlrd==1.2.0")

    fpath = DATA_DIR / "PCA_CDB_0957_F_Census.xls"
    if not fpath.exists():
        raise FileNotFoundError(str(fpath))

    wb = xlrd.open_workbook(str(fpath))
    sh = wb.sheet_by_index(0)

    # Row 0 = headers
    headers = [str(sh.cell_value(0, c)).strip() for c in range(sh.ncols)]
    col_idx = {h: i for i, h in enumerate(headers)}

    aliases       = _load_aliases()
    unmatched     = []
    booth_agg: dict[str, dict] = {}  # booth_id → aggregated values

    for row_idx in range(1, sh.nrows):
        level    = str(sh.cell_value(row_idx, col_idx.get("Level", -1))).strip()
        district = str(sh.cell_value(row_idx, col_idx.get("District_Name", -1))).strip()

        if level != "VILLAGE" or "Gorakhpur" not in district:
            continue

        name = str(sh.cell_value(row_idx, col_idx.get("Name", -1))).strip()
        booth_id = aliases.get(name.lower()) or aliases.get(name.lower().replace(" ", ""))

        row_data: dict = {}
        for src_col, out_col in COLUMN_MAP.items():
            idx = col_idx.get(src_col)
            if idx is not None:
                try:
                    row_data[out_col] = float(sh.cell_value(row_idx, idx) or 0)
                except (ValueError, TypeError):
                    row_data[out_col] = 0.0

        if booth_id:
            if booth_id not in booth_agg:
                booth_agg[booth_id] = {k: 0.0 for k in row_data if k not in ("village_name", "level", "district_name")}
                booth_agg[booth_id]["village_count"] = 0
            for k, v in row_data.items():
                if k in booth_agg[booth_id]:
                    booth_agg[booth_id][k] += v
            booth_agg[booth_id]["village_count"] += 1
        else:
            unmatched.append({"village": name, "district": district})

    # Write unmatched for human review
    out_path = SEEDS_DIR / "unmatched_villages.json"
    SEEDS_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(unmatched, f, ensure_ascii=False, indent=2)
    logger.info("Wrote %d unmatched villages to %s", len(unmatched), out_path)

    # Update booth_master with demographic columns via ALTER + UPDATE
    matched = 0
    with engine.connect() as conn:
        # Ensure extra columns exist (safe to run multiple times)
        for col_def in [
            ("census_total_pop",    "INTEGER DEFAULT 0"),
            ("census_sc_pop",       "INTEGER DEFAULT 0"),
            ("census_st_pop",       "INTEGER DEFAULT 0"),
            ("census_literate_pct", "FLOAT   DEFAULT 0"),
            ("census_workers_pct",  "FLOAT   DEFAULT 0"),
            ("census_hh_count",     "INTEGER DEFAULT 0"),
            ("census_village_count","INTEGER DEFAULT 0"),
        ]:
            try:
                conn.execute(text(
                    f"ALTER TABLE booth_master ADD COLUMN IF NOT EXISTS {col_def[0]} {col_def[1]}"
                ))
            except Exception:
                pass  # column already exists
        conn.commit()

        for booth_id, agg in booth_agg.items():
            total_pop = agg.get("total_population", 1) or 1
            literate_pct = round(agg.get("literate_count", 0) / total_pop * 100, 1)
            workers_pct  = round(agg.get("total_workers",   0) / total_pop * 100, 1)
            conn.execute(
                text("""
                    UPDATE booth_master SET
                        census_total_pop     = :total_pop,
                        census_sc_pop        = :sc_pop,
                        census_st_pop        = :st_pop,
                        census_literate_pct  = :literate_pct,
                        census_workers_pct   = :workers_pct,
                        census_hh_count      = :hh_count,
                        census_village_count = :village_count
                    WHERE booth_id = :booth_id
                """),
                {
                    "booth_id":      booth_id,
                    "total_pop":     int(agg.get("total_population", 0)),
                    "sc_pop":        int(agg.get("sc_population", 0)),
                    "st_pop":        int(agg.get("st_population", 0)),
                    "literate_pct":  literate_pct,
                    "workers_pct":   workers_pct,
                    "hh_count":      int(agg.get("household_count", 0)),
                    "village_count": int(agg.get("village_count", 0)),
                },
            )
            matched += 1
        conn.commit()

    logger.info("Updated %d booths with census data | %d villages unmatched", matched, len(unmatched))
    return matched, len(unmatched)


def run():
    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    matched, unmatched = load_census_to_booth(engine)
    logger.info("Census ETL complete: %d matched, %d unmatched → check data/seeds/unmatched_villages.json",
                matched, unmatched)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()
