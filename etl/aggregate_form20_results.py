"""
ETL: Aggregate Form-20 booth-level votes → constituency-level candidate results

Reads parsed Form-20 JSON files (data/Form20_JSON/) and sums per-candidate votes
across all polling stations to produce constituency-level result facts, then upserts
into candidate_party_history.

This is the primary results source for Vidhan Sabha elections — no external scraping
needed because Form-20 ECI data is already in the repo.

Results source priority (per README):
  1. form20 — ECI Form-20 XLS/JSON (this module)
  2. eci    — CEO UP direct download (future, same schema)
  3. indiavotes — JS-rendered, used for manual cross-check only

Confirmed Form-20 files for AC 322 (Gorakhpur Urban):
  data/Form20_JSON/AC322.json  → 2022 Vidhan Sabha  (471 stations, 15 candidates)
  data/Form20_JSON/322 (4).json → 2019 Lok Sabha    (463 stations, 12 candidates)
  data/Form20_JSON/322 (1).json → likely 2017 VS    (Kruti-encoded, needs kruti_to_unicode first)

Run:
  python -m etl.aggregate_form20_results --ac GKP_322 --year 2022
  python -m etl.aggregate_form20_results --ac GKP_322 --year 2019
"""
from __future__ import annotations

import json
import logging
import os
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parents[1] / "data" / "Form20_JSON"

# Manual overrides: (ac_id, OCR_name_upper, election_year) → canonical candidate_id
# Use when the OCR name is too different from any candidate_master entry for fuzzy matching to work.
CANDIDATE_ID_OVERRIDES: dict[tuple[str, str, int], str] = {
    # OCR "ADIYANATH" (1 T) doesn't fuzzy-match "Yogi Adityanath".
    # GKP_322_YOGI_2022 is the only entry with affidavit data for this candidate.
    ("GKP_322", "ADIYANATH", 2022): "GKP_322_YOGI_2022",
}

# Maps (ac_id, election_year) → JSON filename(s) to try in order
FORM20_FILE_MAP: dict[tuple[str, int], list[str]] = {
    ("GKP_322", 2022): ["AC322.json"],
    ("GKP_322", 2019): ["322 (4).json"],
    # 2017 requires kruti_to_unicode.py first — not included until encoding is fixed
}

# Party name normalisation (raw Form-20 text → canonical)
_PARTY_MAP: dict[str, str] = {
    "B.J.P":           "BJP",
    "B.J.P.":          "BJP",
    "BJP":             "BJP",
    "SAMAJWADI PARTY": "SP",
    "SAMAJWADI":       "SP",
    "BAHUJAN SAMAJ PARTY": "BSP",
    "B.S.P.":          "BSP",
    "BSP":             "BSP",
    "INDIAN NATIONAL CONGRESS": "INC",
    "AAM AADAMI PARTY": "AAP",
    "AAM AADAMI":      "AAP",
    "AAZAD SAMAJ PARTY (KASHI RAM)": "ASP(KR)",
    "AAZAD SAMAJ PARTY": "ASP(KR)",
    "INDEPENDENT":     "IND",
    "INDPENDENT":      "IND",
}

_SKIP_NAMES = {"nota", "none of the above", "total votes", "total votes   se-cured"}


def _norm_party(raw: str) -> str:
    key = (raw or "").strip().upper()
    return _PARTY_MAP.get(key, key[:30] if key else "UNK")


def _slugify(name: str, year: int) -> str:
    slug = re.sub(r"[^A-Z0-9]+", "_", name.strip().upper()).strip("_")
    return f"{slug}_{year}"


def _is_skip(name: str | None) -> bool:
    if not name:
        return True
    return name.strip().lower() in _SKIP_NAMES


def aggregate_candidate_results(
    json_path: Path,
    ac_id: str,
    election_year: int,
) -> list[dict[str, Any]]:
    """
    Read a Form-20 JSON, sum votes per candidate across all booths, and compute
    rank, vote_share_pct, is_winner, result_position_label, and margin fields.

    Returns a list of result-fact dicts ready for upsert into candidate_party_history.
    """
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    # Accumulate votes: candidate_name+party → total
    vote_acc: dict[str, dict] = {}

    for sheet in data.get("sheets", []):
        for ps in sheet.get("polling_stations", []):
            for cv in ps.get("candidate_votes", []):
                name = (cv.get("candidate_name") or "").strip()
                party = (cv.get("party") or "").strip()
                votes = cv.get("votes")

                if _is_skip(name) or votes is None:
                    continue

                # Deduplicate by normalised name (handles minor OCR variation)
                key = re.sub(r"\s+", " ", name.upper())
                if key not in vote_acc:
                    vote_acc[key] = {
                        "candidate_name": name,
                        "party_raw":      party,
                        "party":          _norm_party(party),
                        "total_votes":    0,
                    }
                vote_acc[key]["total_votes"] += int(votes)

    if not vote_acc:
        logger.warning("No candidate vote data found in %s", json_path.name)
        return []

    # Sort by votes descending → assign rank
    ranked = sorted(vote_acc.values(), key=lambda x: x["total_votes"], reverse=True)
    valid_votes_total = sum(r["total_votes"] for r in ranked)

    winner_votes = ranked[0]["total_votes"] if ranked else 0
    runner_up_votes = ranked[1]["total_votes"] if len(ranked) > 1 else 0
    victory_margin = winner_votes - runner_up_votes

    results: list[dict[str, Any]] = []
    for rank, row in enumerate(ranked, start=1):
        votes = row["total_votes"]
        is_winner = rank == 1
        if rank == 1:
            pos_label = "winner"
        elif rank == 2:
            pos_label = "runner_up"
        else:
            pos_label = "other"

        results.append({
            "candidate_id":           _slugify(row["candidate_name"], election_year),
            "candidate_name":         row["candidate_name"],
            "party_id":               row["party"],
            "election_year":          election_year,
            "constituency":           ac_id,
            "votes_received":         votes,
            "vote_share":             round(votes / valid_votes_total * 100, 4) if valid_votes_total else 0,
            "result":                 "won" if is_winner else "lost",
            "margin":                 victory_margin if is_winner else None,
            "rank":                   rank,
            "is_winner":              is_winner,
            "result_position_label":  pos_label,
            "vote_gap_vs_winner":     None if is_winner else (winner_votes - votes),
            "victory_margin_votes":   victory_margin if is_winner else None,
            "valid_votes_total":      valid_votes_total,
            "results_source":         "form20",
            "source_results_url":     str(json_path),
        })

    logger.info(
        "%s %d: %d candidates | winner %s (%d votes, %.1f%%) | margin %d",
        ac_id, election_year, len(results),
        results[0]["candidate_name"], winner_votes,
        results[0]["vote_share"], victory_margin,
    )
    return results


def reconcile_candidate_ids(
    results: list[dict],
    engine: sa.Engine,
    ac_id: str,
    election_year: int,
    threshold: float = 0.80,
) -> list[dict]:
    """
    Map OCR-derived candidate_ids to canonical IDs already in candidate_master.
    Uses fuzzy name matching to handle OCR typos (e.g. ADIYANATH → ADITYANATH).

    Preference order when multiple candidate_master entries match the same name:
      1. Entry with a 'scraped' affidavit (preserves the richer affidavit join)
      2. Entry with any affidavit
      3. Any entry (arbitrary)

    Unmatched rows keep their OCR-derived IDs so they still land in the DB.
    """
    with engine.connect() as conn:
        master_rows = conn.execute(text("""
            SELECT cm.candidate_id, cm.name, ca.parse_status
            FROM candidate_master cm
            LEFT JOIN candidate_affidavits ca ON ca.candidate_id = cm.candidate_id
            WHERE cm.ac_id = :ac_id AND cm.election_year = :year
        """), {"ac_id": ac_id, "year": election_year}).fetchall()

    if not master_rows:
        logger.warning("No candidate_master rows for %s/%d — skipping reconciliation", ac_id, election_year)
        return results

    # Build multi-value lookup: upper_name → list of (candidate_id, display_name, parse_status)
    name_to_candidates: dict[str, list[tuple[str, str, str | None]]] = {}
    for row in master_rows:
        key = row[1].strip().upper()
        name_to_candidates.setdefault(key, []).append((row[0], row[1], row[2]))

    def _best_entry(candidates: list[tuple[str, str, str | None]]) -> tuple[str, str]:
        """Pick the entry that has the richest affidavit, falling back to first."""
        scraped = [c for c in candidates if c[2] == "scraped"]
        with_affidavit = [c for c in candidates if c[2] is not None]
        chosen = (scraped or with_affidavit or candidates)[0]
        return chosen[0], chosen[1]

    master_names = list(name_to_candidates.keys())

    for row in results:
        ocr_upper = row["candidate_name"].strip().upper()

        # 0. Hard-coded override wins over all fuzzy logic
        override_key = (ac_id, ocr_upper, election_year)
        if override_key in CANDIDATE_ID_OVERRIDES:
            row["candidate_id"] = CANDIDATE_ID_OVERRIDES[override_key]
            logger.info("Override applied: OCR '%s' → %s", row["candidate_name"], row["candidate_id"])
            continue

        if ocr_upper in name_to_candidates:
            canonical_id, display_name = _best_entry(name_to_candidates[ocr_upper])
            if row["candidate_id"] != canonical_id:
                logger.info("Exact name match: '%s' → %s", row["candidate_name"], canonical_id)
                row["candidate_id"] = canonical_id
            continue

        best_name, best_score = max(
            ((n, SequenceMatcher(None, ocr_upper, n).ratio()) for n in master_names),
            key=lambda t: t[1],
            default=(None, 0.0),
        )
        if best_score >= threshold and best_name:
            canonical_id, display_name = _best_entry(name_to_candidates[best_name])
            logger.info(
                "Fuzzy match (%.2f): OCR '%s' → master '%s' (%s)",
                best_score, row["candidate_name"], display_name, canonical_id,
            )
            row["candidate_id"] = canonical_id
        else:
            logger.warning(
                "No match for OCR name '%s' (best='%s' %.2f) — keeping id %s",
                row["candidate_name"], best_name, best_score, row["candidate_id"],
            )

    return results


def upsert_results(results: list[dict], engine: sa.Engine) -> int:
    """
    Upsert result facts into candidate_party_history.
    The unique constraint (candidate_id, election_year, constituency) means
    reruns update existing rows rather than duplicating.
    """
    if not results:
        return 0

    with engine.connect() as conn:
        for row in results:
            conn.execute(text("""
                INSERT INTO candidate_party_history (
                    candidate_id, candidate_name, party_id,
                    election_year, constituency,
                    votes_received, vote_share, result, margin,
                    rank, is_winner, result_position_label,
                    vote_gap_vs_winner, victory_margin_votes, valid_votes_total,
                    results_source, source_results_url
                )
                VALUES (
                    :candidate_id, :candidate_name, :party_id,
                    :election_year, :constituency,
                    :votes_received, :vote_share, :result, :margin,
                    :rank, :is_winner, :result_position_label,
                    :vote_gap_vs_winner, :victory_margin_votes, :valid_votes_total,
                    :results_source, :source_results_url
                )
                ON CONFLICT (candidate_id, election_year, constituency) DO UPDATE SET
                    votes_received        = EXCLUDED.votes_received,
                    vote_share            = EXCLUDED.vote_share,
                    result                = EXCLUDED.result,
                    margin                = EXCLUDED.margin,
                    rank                  = EXCLUDED.rank,
                    is_winner             = EXCLUDED.is_winner,
                    result_position_label = EXCLUDED.result_position_label,
                    vote_gap_vs_winner    = EXCLUDED.vote_gap_vs_winner,
                    victory_margin_votes  = EXCLUDED.victory_margin_votes,
                    valid_votes_total     = EXCLUDED.valid_votes_total,
                    results_source        = EXCLUDED.results_source,
                    source_results_url    = EXCLUDED.source_results_url
            """), row)
        conn.commit()

    logger.info("Upserted %d result rows", len(results))
    return len(results)


def run(ac_id: str = "GKP_322", election_year: int = 2022) -> int:
    key = (ac_id, election_year)
    filenames = FORM20_FILE_MAP.get(key)
    if not filenames:
        logger.error(
            "No Form-20 file mapping for (%s, %d). "
            "Add an entry to FORM20_FILE_MAP or pass --json directly.",
            ac_id, election_year,
        )
        return 0

    for fname in filenames:
        json_path = DATA_DIR / fname
        if json_path.exists():
            break
    else:
        logger.error("Form-20 JSON not found. Tried: %s", filenames)
        return 0

    results = aggregate_candidate_results(json_path, ac_id, election_year)
    if not results:
        return 0

    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    results = reconcile_candidate_ids(results, engine, ac_id, election_year)
    return upsert_results(results, engine)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    import argparse

    p = argparse.ArgumentParser(description="Aggregate Form-20 results into candidate_party_history")
    p.add_argument("--ac",   default="GKP_322", help="Canonical ac_id (e.g. GKP_322)")
    p.add_argument("--year", type=int, default=2022, help="Election year")
    p.add_argument("--json", default=None, help="Override: direct path to Form-20 JSON file")
    args = p.parse_args()

    if args.json:
        results = aggregate_candidate_results(Path(args.json), args.ac, args.year)
        engine = sa.create_engine(os.environ["POSTGRES_URL"])
        results = reconcile_candidate_ids(results, engine, args.ac, args.year)
        n = upsert_results(results, engine)
    else:
        n = run(args.ac, args.year)

    print(f"Done — {n} rows upserted")
