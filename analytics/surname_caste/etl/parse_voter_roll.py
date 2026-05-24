"""
parse_voter_roll.py
====================
Loads all PoolBoothData_JSON/part_*.json files and normalises them
into a single flat Parquet file.

Output: data/transformed/voter_roll_normalized.parquet
Schema:
    voter_id        str
    ac_number       int     (from file metadata, always 322 for current dataset)
    part_number     int     (= electoral roll part, primary linkage key)
    section_name    str     (locality name, OCR-transliterated)
    full_name       str
    relation_type   str     (Father / Husband / Mother)
    relation_name   str
    house_number    str
    gender          str     (Male / Female / Unknown)
    age             int
    photo_available bool
"""

from __future__ import annotations

import glob
import json
import logging
from pathlib import Path

import pandas as pd
from tqdm import tqdm

log = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[3]
VOTER_ROLL_DIR = ROOT / "data" / "PoolBoothData_JSON"
OUTPUT_PATH = ROOT / "data" / "transformed" / "voter_roll_normalized.parquet"


def load_part_file(filepath: Path) -> list[dict]:
    """Parse a single part_*.json voter roll file into a list of flat records."""
    with open(filepath, encoding="utf-8") as fh:
        data = json.load(fh)

    meta = data.get("metadata", {})
    ac_info = meta.get("assembly_constituency", {})
    ac_number = int(ac_info.get("number", 0))
    part_number = int(meta.get("part_number", 0))
    # Fallback: derive part_number from filename if missing in metadata
    if part_number == 0:
        stem = filepath.stem  # e.g. "part_007"
        try:
            part_number = int(stem.split("_")[-1])
        except ValueError:
            pass

    records: list[dict] = []
    for voter in data.get("voter_records", []):
        records.append(
            {
                "voter_id": str(voter.get("voter_id", "")),
                "ac_number": ac_number,
                "part_number": part_number,
                "section_name": str(voter.get("section_name", "") or ""),
                "full_name": str(voter.get("name", "") or ""),
                "relation_type": str(voter.get("relation_type", "") or ""),
                "relation_name": str(voter.get("relation_name", "") or ""),
                "house_number": str(voter.get("house_number", "") or ""),
                "gender": _normalise_gender(voter.get("gender")),
                "age": _safe_int(voter.get("age")),
                "photo_available": bool(voter.get("photo_available", False)),
            }
        )
    return records


def _normalise_gender(raw) -> str:
    if raw is None:
        return "Unknown"
    s = str(raw).strip().capitalize()
    if s in ("Male", "M"):
        return "Male"
    if s in ("Female", "F"):
        return "Female"
    return "Unknown"


def _safe_int(val) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return -1


def parse_voter_roll(
    source_dir: Path = VOTER_ROLL_DIR,
    output_path: Path = OUTPUT_PATH,
    *,
    force: bool = False,
) -> pd.DataFrame:
    """
    Parse all voter roll JSON files and return a normalised DataFrame.
    Writes parquet to *output_path* (skips if file exists and force=False).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists() and not force:
        log.info("Voter roll parquet already exists → loading from cache: %s", output_path)
        return pd.read_parquet(output_path)

    part_files = sorted(source_dir.glob("part_*.json"))
    if not part_files:
        raise FileNotFoundError(f"No part_*.json files found in {source_dir}")

    log.info("Loading %d voter roll part files…", len(part_files))
    all_records: list[dict] = []
    for fp in tqdm(part_files, desc="Voter roll parts", unit="file"):
        try:
            all_records.extend(load_part_file(fp))
        except Exception as exc:
            log.warning("Skipping %s — parse error: %s", fp.name, exc)

    df = pd.DataFrame(all_records)

    # Dedup: voter_id should be unique; keep first occurrence
    before = len(df)
    df = df.drop_duplicates(subset=["voter_id"], keep="first")
    dupes = before - len(df)
    if dupes:
        log.warning("Dropped %d duplicate voter_ids", dupes)

    log.info(
        "Voter roll: %d voters across %d parts, %d ACs",
        len(df),
        df["part_number"].nunique(),
        df["ac_number"].nunique(),
    )

    df.to_parquet(output_path, index=False)
    log.info("Saved → %s", output_path)
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    df = parse_voter_roll(force=True)
    print(df.head())
    print(df.dtypes)
    print(f"\nTotal voters: {len(df):,}")
    print(f"Parts covered: {sorted(df['part_number'].unique())}")
