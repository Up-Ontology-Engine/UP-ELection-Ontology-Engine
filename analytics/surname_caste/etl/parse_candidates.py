"""
parse_candidates.py
====================
Normalises the candidate records JSON and derives:
- candidate_surname  (last word of full name, upper-cased)
- election_winner    (Position == 1)
- ac_serial_map      mapping serial# → candidate for AC 322

Output: data/transformed/candidates_normalized.parquet

Also writes: data/transformed/ac322_serial_candidate_map.json
  { "1": {"candidate_name": "RAVI KISHAN", "party": "BJP"}, ... }
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd
from tqdm import tqdm

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
CANDIDATE_FILE = ROOT / "data" / "candidate records" / "gorakhpur_political_influencer_candidate_records.json"
TRANSFORMED = ROOT / "data" / "transformed"
OUT_CANDIDATES = TRANSFORMED / "candidates_normalized.parquet"
OUT_SERIAL_MAP = TRANSFORMED / "ac322_serial_candidate_map.json"

# AC 322 = Gorakhpur Urban / Gorakhpur City
AC322_NAMES = {"322", "GORAKHPUR URBAN", "GORAKHPUR-URBAN", "GORAKHPUR CITY"}


def _safe_float(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _safe_int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _extract_surname(full_name: str) -> str:
    """Return last word of name, upper-cased. Strips titles."""
    _TITLES = {"SHRI", "SMT", "DR", "PROF", "MR", "MRS", "NONE", "OF", "THE", "ABOVE"}
    tokens = [t.strip() for t in str(full_name).upper().split() if t.strip()]
    # Remove known non-surname tokens from the end
    while tokens and tokens[-1] in _TITLES:
        tokens.pop()
    return tokens[-1] if tokens else "UNKNOWN"


def parse_candidates(
    source_file: Path = CANDIDATE_FILE,
    output_path: Path = OUT_CANDIDATES,
    serial_map_path: Path = OUT_SERIAL_MAP,
    *,
    force: bool = False,
) -> pd.DataFrame:
    """Parse candidate records JSON and write normalised parquet."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists() and not force:
        log.info("Candidates parquet cached → %s", output_path)
        return pd.read_parquet(output_path)

    if not source_file.exists():
        raise FileNotFoundError(f"Candidate records not found: {source_file}")

    log.info("Loading candidate records from %s", source_file)
    with open(source_file, encoding="utf-8") as fh:
        raw = json.load(fh)

    rows = []
    for rec in tqdm(raw, desc="Candidates", unit="record"):
        candidate_name = str(rec.get("Candidate", "") or "").strip()
        if not candidate_name or candidate_name.lower() in ("none of the above", "nota"):
            candidate_name_clean = "NOTA"
            candidate_surname = "NOTA"
        else:
            candidate_name_clean = candidate_name.upper()
            candidate_surname = _extract_surname(candidate_name_clean)

        rows.append(
            {
                "constituency_no": str(rec.get("Constituency_No", "") or "").strip(),
                "constituency_name": str(rec.get("Constituency_Name", "") or "").strip().upper(),
                "year": _safe_int(rec.get("Year")),
                "election_type": str(rec.get("Election_Type", "") or "").strip(),
                "position": _safe_int(rec.get("Position")),
                "candidate_name": candidate_name_clean,
                "candidate_surname": candidate_surname,
                "party": str(rec.get("Party", "") or "").strip().upper(),
                "sex": str(rec.get("Sex", "") or "").strip().upper(),
                "age": _safe_int(rec.get("Age")),
                "votes": _safe_int(rec.get("Votes")),
                "valid_votes": _safe_int(rec.get("Valid_Votes")),
                "electors": _safe_int(rec.get("Electors")),
                "vote_share_pct": _safe_float(rec.get("Vote_Share_Percentage")),
                "turnout_pct": _safe_float(rec.get("Turnout_Percentage")),
                "margin": _safe_int(rec.get("Margin")),
                "margin_pct": _safe_float(rec.get("Margin_Percentage")),
                "n_candidates": _safe_int(rec.get("N_Cand")),
                "deposit_lost": str(rec.get("Deposit_Lost", "") or "").lower() == "yes",
                "incumbent": str(rec.get("Incumbent", "") or "").upper() == "TRUE",
                "winner": _safe_int(rec.get("Position")) == 1,
                "pid": str(rec.get("pid", "") or "").strip(),
                "education": str(rec.get("MyNeta_education", "") or "").strip(),
                "profession": str(rec.get("TCPD_Prof_Main", "") or "").strip(),
                "district": str(rec.get("District_Name", "") or "").strip().upper(),
            }
        )

    df = pd.DataFrame(rows)
    log.info(
        "Candidates: %d records, %d constituencies, years: %s",
        len(df),
        df["constituency_no"].nunique(),
        sorted(df["year"].dropna().unique().astype(int).tolist()),
    )

    df.to_parquet(output_path, index=False)
    log.info("Saved → %s", output_path)

    # Build serial→candidate map for AC 322
    _build_serial_map(df, serial_map_path)

    return df


def _build_serial_map(df: pd.DataFrame, output_path: Path) -> dict:
    """
    For AC 322, build a {serial_number: {candidate_name, party}} map.
    Serial order is determined by ballot order (position in election) — we use
    the 'position' field sorted ascending within each year. When position is not
    meaningful for serial order, we sort by candidate name alphabetically as
    ballots in India are listed alphabetically.
    """
    # Filter to AC 322, pick the most recent election year
    mask = df["constituency_no"].isin(["322"]) | df["constituency_name"].str.contains(
        "GORAKHPUR", na=False
    )
    df_322 = df[mask & (df["constituency_no"] == "322")].copy()

    if df_322.empty:
        log.warning("No records found for AC 322 — serial map will be empty")
        serial_map: dict = {}
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(serial_map, fh, ensure_ascii=False, indent=2)
        return serial_map

    # Latest year
    latest_year = int(df_322["year"].max())
    df_yr = df_322[df_322["year"] == latest_year].copy()

    # Sort candidates alphabetically by name (ballot order in UP elections)
    df_yr = df_yr.sort_values("candidate_name").reset_index(drop=True)
    df_yr["serial"] = df_yr.index + 1  # 1-based serial

    serial_map = {}
    for _, row in df_yr.iterrows():
        serial_map[str(int(row["serial"]))] = {
            "candidate_name": row["candidate_name"],
            "party": row["party"],
            "votes": int(row["votes"]) if row["votes"] else None,
            "position": int(row["position"]) if row["position"] else None,
            "winner": bool(row["winner"]),
            "candidate_surname": row["candidate_surname"],
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(serial_map, fh, ensure_ascii=False, indent=2)
    log.info("AC 322 serial map written → %s  (%d candidates)", output_path, len(serial_map))

    return serial_map


def load_serial_map(path: Path = OUT_SERIAL_MAP) -> dict:
    """Load the AC 322 serial→candidate map. Returns {} if not found."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    df = parse_candidates(force=True)
    print(df[["constituency_no", "constituency_name", "year", "candidate_name",
              "candidate_surname", "party", "winner"]].head(20).to_string())
