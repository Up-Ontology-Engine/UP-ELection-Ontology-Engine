"""
parse_form20.py
================
Parses Form 20 JSON files (booth-level vote counts) into two normalised outputs:

1. form20_ac322_by_serial.parquet
   — AC 322 only (station names garbled, no candidate names)
   — Keeps candidate votes by serial number; candidate names resolved separately

2. form20_ac_named.parquet
   — ACs 320–328 from the AC*.json files (full candidate names & parties)
   — One row per (ac_number, polling_station_number, candidate_name, party)

Both outputs include:
    ac_number, ps_number, ps_name, total_electors, turnout_total,
    serial (for 322) / candidate_name + party (for named),
    votes, total_valid_votes, vote_share
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd
from tqdm import tqdm

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
FORM20_DIR = ROOT / "data" / "Form20_JSON"
TRANSFORMED = ROOT / "data" / "transformed"

OUT_322 = TRANSFORMED / "form20_ac322_by_serial.parquet"
OUT_NAMED = TRANSFORMED / "form20_ac_named.parquet"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _safe_int(v) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _load_json(fp: Path) -> dict:
    with open(fp, encoding="utf-8") as fh:
        return json.load(fh)


# ── AC 322 parser ─────────────────────────────────────────────────────────────

def _parse_ac322_sheet(sheet: dict) -> list[dict]:
    """
    Parse one sheet from 322.json.
    Candidate names are placeholder strings → we keep serial numbers only.
    """
    rows: list[dict] = []
    for ps in sheet.get("polling_stations", []):
        ac_num = _safe_int(ps.get("ac_number", 322))
        ps_num = _safe_int(ps.get("polling_station_number", 0))
        ps_name = str(ps.get("polling_station_name", "") or "")
        total_electors = _safe_int(ps.get("total_electors", 0))
        turnout_total = _safe_int(ps.get("turnout_total", 0))
        turnout_male = _safe_int(ps.get("turnout_male", 0))
        turnout_female = _safe_int(ps.get("turnout_female", 0))

        cand_votes = ps.get("candidate_votes", [])
        # total valid votes = sum of all candidate votes
        total_valid = sum(_safe_int(c.get("votes")) for c in cand_votes)

        for cand in cand_votes:
            votes = _safe_int(cand.get("votes"))
            rows.append(
                {
                    "ac_number": ac_num,
                    "ps_number": ps_num,
                    "ps_name": ps_name,
                    "total_electors": total_electors,
                    "turnout_total": turnout_total,
                    "turnout_male": turnout_male,
                    "turnout_female": turnout_female,
                    "serial": _safe_int(cand.get("serial", 0)),
                    "votes": votes,
                    "total_valid_votes": total_valid,
                    "vote_share": round(votes / total_valid, 4) if total_valid else 0.0,
                }
            )
    return rows


def parse_form20_ac322(
    form20_dir: Path = FORM20_DIR,
    output_path: Path = OUT_322,
    *,
    force: bool = False,
) -> pd.DataFrame:
    """Parse AC 322 Form20 (serial-number only) files."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not force:
        log.info("AC322 parquet cached → %s", output_path)
        return pd.read_parquet(output_path)

    # Use only AC322.json (Vidhan Sabha 2022), ignoring 322 (4).json (Lok Sabha)
    files_322 = sorted(form20_dir.glob("AC322.json"))
    if not files_322:
        raise FileNotFoundError(f"No AC322.json file found in {form20_dir}")

    all_rows: list[dict] = []
    for fp in tqdm(files_322, desc="AC322 Form20", unit="file"):
        try:
            data = _load_json(fp)
            sheets = data.get("sheets", [data])  # some files are wrapped
            for sheet in sheets:
                all_rows.extend(_parse_ac322_sheet(sheet))
        except Exception as exc:
            log.warning("Skipping %s: %s", fp.name, exc)

    df = pd.DataFrame(all_rows)
    if df.empty:
        log.warning("AC 322 Form20 produced 0 rows")
        return df

    # Deduplicate: if multiple files overlap on (ps_number, serial), keep first
    df = df.drop_duplicates(subset=["ps_number", "serial"], keep="first")
    log.info("AC 322 Form20: %d rows, %d polling stations", len(df), df["ps_number"].nunique())

    df.to_parquet(output_path, index=False)
    log.info("Saved → %s", output_path)
    return df


# ── Named AC parser (320–328) ─────────────────────────────────────────────────

def _parse_named_sheet(sheet: dict, source_ac: int | None = None) -> list[dict]:
    """
    Parse one sheet from AC3*.json files where candidate_name and party are real.
    """
    rows: list[dict] = []
    for ps in sheet.get("polling_stations", []):
        ac_num = _safe_int(ps.get("ac_number", source_ac or 0))
        ps_num = _safe_int(ps.get("polling_station_number", 0))
        ps_name = str(ps.get("polling_station_name", "") or "")
        total_electors = _safe_int(ps.get("total_electors", 0))
        turnout_total = _safe_int(ps.get("turnout_total", 0))
        turnout_male = _safe_int(ps.get("turnout_male", 0))
        turnout_female = _safe_int(ps.get("turnout_female", 0))

        cand_votes = ps.get("candidate_votes", [])
        total_valid = sum(_safe_int(c.get("votes")) for c in cand_votes)

        ps_winner = None
        max_votes = -1

        for cand in cand_votes:
            cname = str(cand.get("candidate_name", "") or "").strip()
            party = str(cand.get("party", "") or "").strip()
            votes = _safe_int(cand.get("votes"))

            # Skip placeholder entries
            if cname.lower() in ("candidate", "", "nota"):
                continue

            if votes > max_votes:
                max_votes = votes
                ps_winner = cname

            rows.append(
                {
                    "ac_number": ac_num,
                    "ps_number": ps_num,
                    "ps_name": ps_name,
                    "total_electors": total_electors,
                    "turnout_total": turnout_total,
                    "turnout_male": turnout_male,
                    "turnout_female": turnout_female,
                    "candidate_name": cname,
                    "party": party,
                    "votes": votes,
                    "total_valid_votes": total_valid,
                    "vote_share": round(votes / total_valid, 4) if total_valid else 0.0,
                }
            )

        # Annotate winner
        for row in rows[-len(cand_votes):]:
            row["ps_winner"] = ps_winner

    return rows


def parse_form20_named(
    form20_dir: Path = FORM20_DIR,
    output_path: Path = OUT_NAMED,
    *,
    force: bool = False,
) -> pd.DataFrame:
    """Parse named AC Form20 files (AC320.json–AC328.json)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not force:
        log.info("Named AC parquet cached → %s", output_path)
        return pd.read_parquet(output_path)

    ac_files = sorted(form20_dir.glob("AC3*.json"))
    if not ac_files:
        raise FileNotFoundError(f"No AC3*.json files found in {form20_dir}")

    all_rows: list[dict] = []
    for fp in tqdm(ac_files, desc="Named AC Form20", unit="file"):
        try:
            data = _load_json(fp)
            # Extract AC number from filename (e.g. AC320.json → 320)
            stem = fp.stem  # "AC320"
            try:
                source_ac = int("".join(filter(str.isdigit, stem)))
            except ValueError:
                source_ac = None

            sheets = data.get("sheets", [data])
            for sheet in sheets:
                all_rows.extend(_parse_named_sheet(sheet, source_ac))
        except Exception as exc:
            log.warning("Skipping %s: %s", fp.name, exc)

    df = pd.DataFrame(all_rows)
    if df.empty:
        log.warning("Named AC Form20 produced 0 rows")
        return df

    df = df.drop_duplicates(subset=["ac_number", "ps_number", "candidate_name"], keep="first")
    log.info(
        "Named ACs Form20: %d rows, %d ACs, %d polling stations",
        len(df),
        df["ac_number"].nunique(),
        df.groupby("ac_number")["ps_number"].nunique().sum(),
    )

    df.to_parquet(output_path, index=False)
    log.info("Saved → %s", output_path)
    return df


# ── Convenience wrapper ────────────────────────────────────────────────────────

def parse_all_form20(force: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse both Form20 variants. Returns (df_322, df_named)."""
    df_322 = parse_form20_ac322(force=force)
    df_named = parse_form20_named(force=force)
    return df_322, df_named


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    d1, d2 = parse_all_form20(force=True)
    print("AC322 rows:", len(d1), "| polling stations:", d1["ps_number"].nunique())
    print("Named AC rows:", len(d2), "| ACs:", d2["ac_number"].unique())
