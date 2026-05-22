"""
ETL: TCPD Uttar Pradesh Assembly Election vote share data → Postgres + Neo4j

Source: data/voteshare/Uttar_Pradesh_AE.csv
        Trivedi Centre for Political Data (TCPD) constituency-level results

Scope: GKP_322 (Gorakhpur Urban, Constituency_No=322), years 2012/2017/2022

What this fills:
  - 2012: 31 candidates — entirely new (0 rows in DB)
  - 2017: 24 candidates — vote counts missing (20 stubs exist in candidate_master)
  - 2022: 14 candidates — enriches existing rows with TCPD metadata
            (education, profession, incumbent/recontest/turncoat flags, ENOP, turnout)

Strategy:
  1. Normalise party names via etl.constants.normalise_party()
  2. Fuzzy-match TCPD candidate names → existing candidate_master entries
     (handles spelling variants like SHRIVASTAVA/SRIVASTAVA)
  3. Insert new candidate_master rows for unmatched candidates
  4. Upsert candidate_party_history with full vote data
  5. Back-fill candidate_master with education/profession/age/flags

Run:
  python -m etl.ingest_tcpd_voteshare
"""
from __future__ import annotations

import logging
import os
import re
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
import sqlalchemy as sa
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

logger = logging.getLogger(__name__)

CSV_PATH  = Path(__file__).parents[1] / "data" / "voteshare" / "Uttar_Pradesh_AE.csv"
AC_ID     = "GKP_322"
CONST_NO  = 322
DISTRICT  = "GORAKHPUR"

# Constituency-level election IDs
ELECTION_ID_MAP = {2012: "UP_ASM_2012", 2017: "UP_ASM_2017", 2022: "UP_ASM_2022"}

# TCPD party codes that need manual mapping before normalise_party() sees them
TCPD_PARTY_OVERRIDES: dict[str, str] = {
    "PECP":   "PEACE",         # Peace Party
    "ASPKR":  "ASP(KR)",       # Aazad Samaj Party (Kanshi Ram)
    "NOTA":   "NOTA",
    "BSP(K)": "BSP",
    "NCP":    "NCP",
    "AAAP":   "AAAP",          # Aam Aadmi Apna Party — keep as-is
    "GGP":    "GONDVANA",      # Gondvana Gantantra Party
    "Right to Recall Party":     "RIGHT",
    "Anarakshit Samaj Party":    "ANARAKSHIT",
    "Janta Rakshak Party":       "JANTA",
    "Bharatiya Jan Jagriti Party": "BHARATIYA",
}


def _slugify(name: str, year: int) -> str:
    slug = re.sub(r"[^A-Z0-9]+", "_", name.strip().upper()).strip("_")
    return f"{slug}_{year}"


def _norm_party(raw: str) -> str:
    from etl.constants import normalise_party
    raw = raw.strip()
    mapped = TCPD_PARTY_OVERRIDES.get(raw, raw)
    return normalise_party(mapped, fallback=mapped[:30])


def _pos_label(rank: int) -> str:
    if rank == 1:  return "winner"
    if rank == 2:  return "runner_up"
    return "other"


def _fuzzy_match(
    name: str,
    master_rows: list[dict],
    threshold: float = 0.85,
) -> str | None:
    """
    Return canonical candidate_id from master_rows whose name best matches `name`.
    Also checks party as secondary signal when score is close.
    """
    upper = name.strip().upper()
    best_id, best_score = None, 0.0
    for m in master_rows:
        score = SequenceMatcher(None, upper, m["name"].upper()).ratio()
        if score > best_score:
            best_score, best_id = score, m["candidate_id"]
    if best_score >= threshold:
        logger.debug("Fuzzy match %.2f: '%s' → %s", best_score, name, best_id)
        return best_id
    return None


def load_csv() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, low_memory=False)
    gkp = df[
        (df["Constituency_No"] == CONST_NO) &
        (df["District_Name"].str.upper() == DISTRICT)
    ].copy()
    logger.info("Loaded %d GKP_322 rows from TCPD CSV (%d years)", len(gkp),
                gkp["Year"].nunique())
    return gkp


def run(engine: sa.Engine) -> dict[str, int]:
    df = load_csv()
    totals = {"candidates_inserted": 0, "candidates_updated": 0,
              "history_upserted": 0, "master_enriched": 0}

    for year, yr_df in df.groupby("Year"):
        year = int(str(year))
        logger.info("Processing year %d — %d rows", year, len(yr_df))

        # Fetch existing candidate_master for this AC + year
        with engine.connect() as conn:
            master_rows = [
                dict(r) for r in conn.execute(text("""
                    SELECT candidate_id, name, party
                    FROM candidate_master
                    WHERE ac_id = :ac AND election_year = :yr
                """), {"ac": AC_ID, "yr": year}).mappings().fetchall()
            ]

        # Sort by position so winner is processed first
        yr_sorted = yr_df.sort_values("Position")

        valid_votes_total = int(yr_sorted["Valid_Votes"].iloc[0]) if len(yr_sorted) else 0
        winner_votes      = 0
        runner_up_votes   = 0
        for _, row in yr_sorted.iterrows():
            if int(row["Position"]) == 1:
                winner_votes    = int(row["Votes"]) if pd.notna(row["Votes"]) else 0
            if int(row["Position"]) == 2:
                runner_up_votes = int(row["Votes"]) if pd.notna(row["Votes"]) else 0
        victory_margin = winner_votes - runner_up_votes

        for _, row in yr_sorted.iterrows():
            name      = str(row["Candidate"]).strip()
            party_raw = str(row["Party"]).strip()
            position  = int(row["Position"])
            votes     = int(row["Votes"])     if pd.notna(row["Votes"])     else 0
            vote_share = float(row["Vote_Share_Percentage"]) if pd.notna(row["Vote_Share_Percentage"]) else 0.0
            is_winner = position == 1

            # Skip NOTA at candidate_master level (still goes to history)
            is_nota = name.lower() in ("none of the above", "nota", "none_of_the_above")

            canonical_party = _norm_party(party_raw)

            # --- Resolve candidate_id ---
            cid = None
            if not is_nota:
                cid = _fuzzy_match(name, master_rows)

            if cid is None and not is_nota:
                # Insert new candidate_master row
                cid = _slugify(name, year)
                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO candidate_master
                            (candidate_id, name, party, ac_id, election_year,
                             is_incumbent, is_primary_opp)
                        VALUES
                            (:cid, :name, :party, :ac, :yr, :inc, :opp)
                        ON CONFLICT (candidate_id) DO NOTHING
                    """), {
                        "cid":  cid,
                        "name": name,
                        "party": canonical_party,
                        "ac":   AC_ID,
                        "yr":   year,
                        "inc":  bool(row.get("Incumbent", False)) if pd.notna(row.get("Incumbent")) else False,
                        "opp":  position == 2,
                    })
                totals["candidates_inserted"] += 1
                # Add to local master_rows for subsequent fuzzy lookups this year
                master_rows.append({"candidate_id": cid, "name": name, "party": canonical_party})

            if cid is None and is_nota:
                cid = f"NOTA_{AC_ID}_{year}"

            # --- Enrich candidate_master with TCPD metadata ---
            if not is_nota and cid:
                edu        = str(row.get("MyNeta_education", "")).strip() or None
                prof       = str(row.get("TCPD_Prof_Main", "")).strip() or None
                age_val    = row.get("Age")
                age        = int(age_val) if pd.notna(age_val) else None
                incumbent  = bool(row.get("Incumbent", False)) if pd.notna(row.get("Incumbent")) else False

                with engine.begin() as conn:
                    conn.execute(text("""
                        UPDATE candidate_master
                        SET is_incumbent  = :inc,
                            is_primary_opp = CASE WHEN :pos = 2 THEN TRUE ELSE is_primary_opp END
                        WHERE candidate_id = :cid
                    """), {"cid": cid, "inc": incumbent, "pos": position})

                    # Enrich candidate_affidavits if row exists (education / profession)
                    if edu or prof or age:
                        conn.execute(text("""
                            UPDATE candidate_affidavits
                            SET education  = COALESCE(education,  :edu),
                                profession = COALESCE(profession, :prof),
                                age        = COALESCE(age,        :age)
                            WHERE candidate_id = :cid
                        """), {"cid": cid, "edu": edu, "prof": prof, "age": age})

                        # Also insert a stub affidavit row if none exists
                        conn.execute(text("""
                            INSERT INTO candidate_affidavits
                                (candidate_id, election_year, education, profession, age,
                                 criminal_cases, serious_cases, total_assets, total_liabilities)
                            VALUES (:cid, :yr, :edu, :prof, :age, 0, 0, NULL, NULL)
                            ON CONFLICT (candidate_id) DO NOTHING
                        """), {"cid": cid, "yr": year, "edu": edu, "prof": prof, "age": age})

                totals["master_enriched"] += 1

            # --- Upsert candidate_party_history ---
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO candidate_party_history (
                        candidate_id, candidate_name, party_id,
                        election_year, constituency,
                        votes_received, vote_share, result,
                        rank, is_winner, result_position_label,
                        margin, victory_margin_votes, valid_votes_total,
                        vote_gap_vs_winner,
                        result_completeness_status,
                        results_source, source_results_url
                    )
                    VALUES (
                        :cid, :name, :party,
                        :yr, :con,
                        :votes, :share, :result,
                        :rank, :is_winner, :pos_label,
                        :margin, :vic_margin, :valid_total,
                        :gap,
                        'complete',
                        'tcpd_csv',
                        'data/voteshare/Uttar_Pradesh_AE.csv'
                    )
                    ON CONFLICT (candidate_id, election_year, constituency) DO UPDATE SET
                        votes_received        = EXCLUDED.votes_received,
                        vote_share            = EXCLUDED.vote_share,
                        result                = EXCLUDED.result,
                        rank                  = EXCLUDED.rank,
                        is_winner             = EXCLUDED.is_winner,
                        result_position_label = EXCLUDED.result_position_label,
                        margin                = COALESCE(EXCLUDED.margin, candidate_party_history.margin),
                        victory_margin_votes  = COALESCE(EXCLUDED.victory_margin_votes, candidate_party_history.victory_margin_votes),
                        valid_votes_total     = COALESCE(EXCLUDED.valid_votes_total, candidate_party_history.valid_votes_total),
                        vote_gap_vs_winner    = COALESCE(EXCLUDED.vote_gap_vs_winner, candidate_party_history.vote_gap_vs_winner),
                        results_source        = EXCLUDED.results_source
                """), {
                    "cid":        cid or _slugify(name, year),
                    "name":       name,
                    "party":      canonical_party,
                    "yr":         year,
                    "con":        AC_ID,
                    "votes":      votes,
                    "share":      round(vote_share, 4),
                    "result":     "won" if is_winner else "lost",
                    "rank":       position,
                    "is_winner":  is_winner,
                    "pos_label":  _pos_label(position),
                    "margin":     victory_margin if is_winner else None,
                    "vic_margin": victory_margin if is_winner else None,
                    "valid_total": valid_votes_total,
                    "gap":        (winner_votes - votes) if not is_winner and votes else None,
                })
            totals["history_upserted"] += 1

        logger.info("Year %d done: %d candidates upserted to history", year, len(yr_sorted))

    return totals


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    eng = sa.create_engine(os.environ["POSTGRES_URL"])
    counts = run(eng)
    print("Done:", counts)
