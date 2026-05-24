"""
aggregator.py
==============
Aggregates voter roll surnames + caste groups per booth and joins with
Form 20 election results to produce the analysis dataset.

Steps
-----
1. Load voter roll with surnames (from surname_extractor + caste_mapper)
2. Load Form 20 booth results (AC 322 serial-based)
3. Load candidate serial map (to resolve serial# → party)
4. Load linkage map (part# ↔ ps# reconciliation)
5. Aggregate caste composition per booth (caste_share%)
6. Join with election results
7. Pivot party votes into wide format

Outputs
-------
data/transformed/caste_booth_analysis.parquet
  One row per booth with:
    - caste_share_<CasteGroup> for every caste group
    - party_share_<PARTY> for every party
    - winner_party, winner_candidate
    - turnout_total, total_electors, match_status
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd
import numpy as np

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
TRANSFORMED = ROOT / "data" / "transformed"

OUT_ANALYSIS = TRANSFORMED / "caste_booth_analysis.parquet"


def _load_json(path: Path) -> dict | list:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def build_caste_booth_analysis(
    *,
    voter_roll_path: Path = TRANSFORMED / "voter_roll_normalised_caste.parquet",
    form20_322_path: Path = TRANSFORMED / "form20_ac322_by_serial.parquet",
    serial_map_path: Path = TRANSFORMED / "ac322_serial_candidate_map.json",
    linkage_map_path: Path = TRANSFORMED / "booth_linkage_map.json",
    output_path: Path = OUT_ANALYSIS,
    force: bool = False,
    min_confidence: str = "VERY_LOW",  # include all confidence levels
    include_suspect: bool = True,
) -> pd.DataFrame:
    """
    Build the joined caste × election results analysis table for AC 322.

    Parameters
    ----------
    min_confidence  : minimum surname confidence to include in caste aggregation
                      Values: HIGH | MEDIUM | LOW | VERY_LOW
    include_suspect : whether to include SUSPECT-linked booths
    """
    if output_path.exists() and not force:
        log.info("Caste booth analysis cached → %s", output_path)
        return pd.read_parquet(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Load inputs ─────────────────────────────────────────────────────────
    log.info("Loading voter roll with caste…")
    vr = pd.read_parquet(voter_roll_path)

    log.info("Loading Form 20 AC 322…")
    f20 = pd.read_parquet(form20_322_path)

    log.info("Loading serial map…")
    serial_map: dict = _load_json(serial_map_path) if serial_map_path.exists() else {}

    log.info("Loading linkage map…")
    linkage_raw = _load_json(linkage_map_path) if linkage_map_path.exists() else []
    linkage = pd.DataFrame(linkage_raw)

    # ── Filter voter roll by confidence ─────────────────────────────────────
    CONF_ORDER = {"HIGH": 4, "MEDIUM": 3, "LOW": 2, "VERY_LOW": 1}
    min_conf_val = CONF_ORDER.get(min_confidence.upper(), 1)
    vr = vr[
        vr["surname_confidence"].map(lambda c: CONF_ORDER.get(str(c).upper(), 0)) >= min_conf_val
    ].copy()

    # ── Filter linkage by match status ───────────────────────────────────────
    valid_statuses = ["MATCHED"]
    if include_suspect:
        valid_statuses.append("SUSPECT")
    valid_parts = set(
        linkage[linkage["match_status"].isin(valid_statuses)]["part_number"].tolist()
    )
    log.info("Using %d valid booths (parts): %s", len(valid_parts), sorted(valid_parts))

    vr_valid = vr[vr["part_number"].isin(valid_parts)].copy()

    # ── Step A: Caste composition per booth ──────────────────────────────────
    log.info("Aggregating caste composition per booth…")

    total_per_booth = vr_valid.groupby("part_number")["voter_id"].count().rename("total_voters")

    caste_counts = (
        vr_valid.groupby(["part_number", "caste_group"])["voter_id"]
        .count()
        .unstack(fill_value=0)
    )

    # Normalise to shares
    caste_shares = caste_counts.div(total_per_booth, axis=0).round(4)
    caste_shares.columns = [f"caste_share_{col}" for col in caste_shares.columns]
    caste_shares = caste_shares.reset_index()

    # ── Step B: Party votes per booth from Form 20 ───────────────────────────
    log.info("Building party vote shares per booth…")

    # Enrich Form20 with candidate/party names using serial map
    def _resolve_party(serial: int) -> str:
        entry = serial_map.get(str(serial), {})
        party = str(entry.get("party", f"SER_{serial}")).upper()
        if party not in ("BJP", "SP", "BSP", "INC"):
            return "OTHER"
        return party

    def _resolve_candidate(serial: int) -> str:
        entry = serial_map.get(str(serial), {})
        return str(entry.get("candidate_name", f"CANDIDATE_{serial}"))

    f20_valid = f20[f20["ps_number"].isin(valid_parts)].copy()
    f20_valid["party"] = f20_valid["serial"].apply(_resolve_party)
    f20_valid["candidate_name"] = f20_valid["serial"].apply(_resolve_candidate)

    # Winner per booth
    idx_max = f20_valid.groupby("ps_number")["votes"].idxmax()
    winners = f20_valid.loc[idx_max][["ps_number", "party", "candidate_name"]].rename(
        columns={"party": "winner_party", "candidate_name": "winner_candidate"}
    )

    # Pivot: one row per booth, one col per party
    party_pivot = (
        f20_valid.pivot_table(
            index="ps_number",
            columns="party",
            values="votes",
            aggfunc="sum",
            fill_value=0,
        )
    )
    total_valid_per_booth = party_pivot.sum(axis=1).rename("total_valid_votes")
    party_shares = party_pivot.div(total_valid_per_booth, axis=0).round(4)
    party_shares.columns = [f"party_share_{col}" for col in party_shares.columns]
    party_shares = party_shares.reset_index().rename(columns={"ps_number": "part_number"})

    total_valid_per_booth = total_valid_per_booth.reset_index().rename(
        columns={"ps_number": "part_number", 0: "total_valid_votes"}
    )

    # ── Step C: Join linkage metadata ────────────────────────────────────────
    linkage_meta = linkage[
        ["part_number", "voter_roll_count", "form20_electors",
         "form20_turnout", "delta_pct", "match_status"]
    ].copy()

    winners = winners.rename(columns={"ps_number": "part_number"})

    # ── Step D: Merge everything ─────────────────────────────────────────────
    log.info("Merging caste shares + party shares + metadata…")

    df = caste_shares.merge(party_shares, on="part_number", how="inner")
    df = df.merge(winners, on="part_number", how="left")
    df = df.merge(total_valid_per_booth, on="part_number", how="left")
    df = df.merge(linkage_meta, on="part_number", how="left")
    df["ac_number"] = 322

    # ── Summary ──────────────────────────────────────────────────────────────
    n_booths = len(df)
    n_caste_cols = sum(1 for c in df.columns if c.startswith("caste_share_"))
    n_party_cols = sum(1 for c in df.columns if c.startswith("party_share_"))
    log.info(
        "Caste booth analysis: %d booths, %d caste groups, %d parties",
        n_booths, n_caste_cols, n_party_cols,
    )

    df.to_parquet(output_path, index=False)
    log.info("Saved → %s", output_path)
    return df


def get_caste_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c.startswith("caste_share_")]


def get_party_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c.startswith("party_share_")]


def get_caste_names(df: pd.DataFrame) -> list[str]:
    return [c.replace("caste_share_", "") for c in get_caste_columns(df)]


def get_party_names(df: pd.DataFrame) -> list[str]:
    return [c.replace("party_share_", "") for c in get_party_columns(df)]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    df = build_caste_booth_analysis(force=True)
    print(f"Shape: {df.shape}")
    print(df[["part_number", "winner_party", "total_valid_votes"]].head(10))
    print("Caste cols:", get_caste_names(df)[:10])
    print("Party cols:", get_party_names(df))
