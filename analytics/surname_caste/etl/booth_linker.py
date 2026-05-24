"""
booth_linker.py
================
Reconciles electoral roll part numbers with Form 20 polling station numbers.

Strategy
--------
Primary key : part_number == polling_station_number  (within same AC)
Validation  : voter_roll_count vs form20_total_electors
              → delta ≤ 20%   → MATCHED
              → 20% < delta ≤ 40% → SUSPECT  (included with flag)
              → delta > 40%   → MISMATCH  (excluded from correlation)
              → no form20 row → NO_FORM20  (voter-only analysis only)

Special case (AC 322)
---------------------
The voter roll has 77 parts (not all sequential, some missing).
The Form20 has 389 polling stations.
Multiple parts may correspond to a single polling station building — they are
treated as a single logical booth in the analysis by grouping on part_number.

Output
------
data/transformed/booth_linkage_map.json
  [
    {
      "ac_number": 322,
      "part_number": 7,
      "ps_number": 7,
      "voter_roll_count": 679,
      "form20_electors": 700,
      "delta_pct": 0.03,
      "match_status": "MATCHED"
    }, ...
  ]
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
TRANSFORMED = ROOT / "data" / "transformed"

OUT_LINKAGE = TRANSFORMED / "booth_linkage_map.json"

# Thresholds
MATCHED_THRESHOLD = 0.20   # ≤ 20% delta → MATCHED
SUSPECT_THRESHOLD = 0.40   # ≤ 40% delta → SUSPECT


def build_linkage_map(
    voter_roll_df: pd.DataFrame,
    form20_df: pd.DataFrame,
    *,
    ac_number: int = 322,
    output_path: Path = OUT_LINKAGE,
    force: bool = False,
) -> pd.DataFrame:
    """
    Build and persist the part → polling-station linkage map.

    Parameters
    ----------
    voter_roll_df  : normalised voter roll DataFrame (from parse_voter_roll)
    form20_df      : Form 20 DataFrame for the target AC (from parse_form20)
                     Must have columns: ps_number, total_electors
    ac_number      : AC to reconcile (default 322)
    output_path    : path to write JSON map
    force          : recompute even if output file exists
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists() and not force:
        log.info("Linkage map cached → %s", output_path)
        df = pd.read_json(output_path)
        return df

    # ── Voter roll side ──────────────────────────────────────────────────────
    vr = voter_roll_df[voter_roll_df["ac_number"] == ac_number].copy()
    vr_counts = (
        vr.groupby("part_number")["voter_id"]
        .count()
        .reset_index()
        .rename(columns={"voter_id": "voter_roll_count"})
    )

    # ── Form 20 side ────────────────────────────────────────────────────────
    # For AC 322 serial-based file we need the per-station electors
    # form20_df has one row per (ps_number, serial); we pick one row per ps
    fm = form20_df[form20_df["ac_number"] == ac_number].copy()
    fm_stations = (
        fm.drop_duplicates(subset=["ps_number"])
        [["ps_number", "total_electors", "turnout_total"]]
        .copy()
    )

    # ── Merge ────────────────────────────────────────────────────────────────
    merged = vr_counts.merge(
        fm_stations.rename(columns={"ps_number": "part_number"}),
        on="part_number",
        how="outer",
    )

    linkage_rows = []
    for _, row in merged.iterrows():
        part_num = int(row["part_number"])
        vr_count = row["voter_roll_count"]
        f20_electors = row["total_electors"]
        turnout = row.get("turnout_total")

        if pd.isna(vr_count):
            status = "NO_VOTER_ROLL"
            delta = None
        elif pd.isna(f20_electors) or f20_electors == 0:
            status = "NO_FORM20"
            delta = None
        else:
            delta = abs(int(vr_count) - int(f20_electors)) / int(f20_electors)
            if delta <= MATCHED_THRESHOLD:
                status = "MATCHED"
            elif delta <= SUSPECT_THRESHOLD:
                status = "SUSPECT"
            else:
                status = "MISMATCH"

        linkage_rows.append(
            {
                "ac_number": ac_number,
                "part_number": part_num,
                "ps_number": part_num,  # primary assumption: same number
                "voter_roll_count": int(vr_count) if not pd.isna(vr_count) else None,
                "form20_electors": int(f20_electors) if not pd.isna(f20_electors) else None,
                "form20_turnout": int(turnout) if (turnout and not pd.isna(turnout)) else None,
                "delta_pct": round(float(delta), 4) if delta is not None else None,
                "match_status": status,
            }
        )

    df_linkage = pd.DataFrame(linkage_rows).sort_values("part_number").reset_index(drop=True)

    # ── Summary log ──────────────────────────────────────────────────────────
    status_counts = df_linkage["match_status"].value_counts().to_dict()
    total = len(df_linkage)
    log.info(
        "Linkage summary for AC %d (%d entries): %s",
        ac_number,
        total,
        " | ".join(f"{k}: {v}" for k, v in sorted(status_counts.items())),
    )

    # ── Persist ──────────────────────────────────────────────────────────────
    records = df_linkage.to_dict(orient="records")
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False, indent=2)
    log.info("Linkage map saved → %s", output_path)

    return df_linkage


def load_linkage_map(path: Path = OUT_LINKAGE) -> pd.DataFrame:
    """Load linkage map from JSON. Returns empty DataFrame if not found."""
    if not path.exists():
        log.warning("Linkage map not found: %s", path)
        return pd.DataFrame()
    return pd.read_json(path)


def get_matched_parts(
    linkage_df: pd.DataFrame,
    include_suspect: bool = True,
) -> list[int]:
    """Return list of part numbers that are MATCHED (and optionally SUSPECT)."""
    statuses = ["MATCHED"]
    if include_suspect:
        statuses.append("SUSPECT")
    return linkage_df[linkage_df["match_status"].isin(statuses)]["part_number"].tolist()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    from analytics.surname_caste.etl.parse_voter_roll import parse_voter_roll
    from analytics.surname_caste.etl.parse_form20 import parse_form20_ac322

    vr = parse_voter_roll()
    f20 = parse_form20_ac322()
    lm = build_linkage_map(vr, f20, force=True)
    print(lm.to_string())
    print(f"\nMatched parts: {get_matched_parts(lm)}")
