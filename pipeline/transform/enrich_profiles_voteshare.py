"""
Enrich GKP_322_candidate_profiles.json with TCPD Uttar_Pradesh_AE.csv data.

Adds per-candidate:
  - election_result: votes, position, vote_share, margin, deposit_lost, etc.
  - personal.sex
  - political: party_type, no_terms, incumbent, turncoat, recontest, contested
  - profession.tcpd_main / tcpd_second

Adds to every profile:
  - constituency_history: full seat results 1962-2022 (winner + runner-up per year)
"""

import csv
import json
import re
from pathlib import Path

CSV_PATH     = Path("data/voteshare/Uttar_Pradesh_AE.csv")
PROFILES_IN  = Path("data/raw/candidates/GKP_322_candidate_profiles.json")
PROFILES_OUT = PROFILES_IN   # overwrite in place


def _norm(name: str) -> str:
    """Normalise candidate name for fuzzy matching."""
    name = name.upper().strip()
    name = re.sub(r"\bDR\.?\s*", "", name)   # strip Dr. prefix
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def _bool(val: str) -> bool | None:
    if val.upper() == "TRUE":
        return True
    if val.upper() == "FALSE":
        return False
    return None


def load_csv() -> list[dict]:
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def build_constituency_history(all_rows: list[dict]) -> list[dict]:
    """All election years at GKP_322, sorted desc, with full candidate results."""
    gkp = [r for r in all_rows if r["Constituency_No"] == "322"]
    by_year: dict[str, list[dict]] = {}
    for r in gkp:
        by_year.setdefault(r["Year"], []).append(r)

    history = []
    for year in sorted(by_year.keys(), reverse=True):
        yr_rows = sorted(by_year[year], key=lambda x: int(x["Position"]))
        winner = yr_rows[0]
        history.append({
            "year": int(year),
            "total_electors": int(winner["Electors"]) if winner["Electors"] else None,
            "valid_votes": int(winner["Valid_Votes"]) if winner["Valid_Votes"] else None,
            "turnout_pct": float(winner["Turnout_Percentage"]) if winner["Turnout_Percentage"] else None,
            "n_candidates": int(winner["N_Cand"]) if winner["N_Cand"] else None,
            "candidates": [
                {
                    "position": int(r["Position"]),
                    "name": r["Candidate"],
                    "party": r["Party"],
                    "votes": int(r["Votes"]) if r["Votes"] else None,
                    "vote_share_pct": float(r["Vote_Share_Percentage"]) if r["Vote_Share_Percentage"] else None,
                    "margin": int(r["Margin"]) if r["Margin"] else None,
                    "deposit_lost": r["Deposit_Lost"].lower() == "yes" if r["Deposit_Lost"] else None,
                    "sex": r["Sex"] or None,
                }
                for r in yr_rows
                if r["Candidate"] != "None Of The Above"
            ],
        })
    return history


def match_row(profile: dict, csv_rows_2022: list[dict]) -> dict | None:
    """Find the matching 2022 CSV row for this profile by name."""
    pname = _norm(profile["personal"]["name"])
    for row in csv_rows_2022:
        if _norm(row["Candidate"]) == pname:
            return row
    return None


def enrich_profile(profile: dict, row: dict) -> dict:
    """Merge CSV fields into the profile dict."""
    # 1. Election result
    profile["election_result_2022"] = {
        "position": int(row["Position"]),
        "votes": int(row["Votes"]) if row["Votes"] else None,
        "valid_votes": int(row["Valid_Votes"]) if row["Valid_Votes"] else None,
        "vote_share_pct": float(row["Vote_Share_Percentage"]) if row["Vote_Share_Percentage"] else None,
        "margin": int(row["Margin"]) if row["Margin"] else None,
        "margin_pct": float(row["Margin_Percentage"]) if row["Margin_Percentage"] else None,
        "deposit_lost": row["Deposit_Lost"].lower() == "yes" if row["Deposit_Lost"] else None,
        "total_electors": int(row["Electors"]) if row["Electors"] else None,
        "turnout_pct": float(row["Turnout_Percentage"]) if row["Turnout_Percentage"] else None,
        "n_candidates_in_contest": int(row["N_Cand"]) if row["N_Cand"] else None,
        "enop": float(row["ENOP"]) if row["ENOP"] else None,
    }

    # 2. Personal enrichment
    profile["personal"]["sex"] = row["Sex"] or None
    profile["personal"]["tcpd_pid"] = row["pid"] or None

    # 3. Political flags
    profile["political"] = {
        "party_type_tcpd": row["Party_Type_TCPD"] or None,
        "times_contested_total": int(row["Contested"]) if row["Contested"] else None,
        "no_terms_won": int(row["No_Terms"]) if row["No_Terms"] else None,
        "is_incumbent": _bool(row["Incumbent"]),
        "is_turncoat": _bool(row["Turncoat"]),
        "did_recontest": _bool(row["Recontest"]),
        "last_party": row["Last_Party"] or None,
        "last_constituency": row["Last_Constituency_Name"] or None,
        "same_constituency": _bool(row["Same_Constituency"]),
        "same_party": _bool(row["Same_Party"]),
    }

    # 4. Profession (TCPD-coded, more systematic than self-declared)
    tcpd_main   = row["TCPD_Prof_Main"] or None
    tcpd_main_d = row["TCPD_Prof_Main_Desc"] or None
    tcpd_sec    = row["TCPD_Prof_Second"] or None
    tcpd_sec_d  = row["TCPD_Prof_Second_Desc"] or None

    profile["profession"]["tcpd_main"] = (
        f"{tcpd_main} ({tcpd_main_d})" if tcpd_main_d else tcpd_main
    )
    profile["profession"]["tcpd_second"] = (
        f"{tcpd_sec} ({tcpd_sec_d})" if tcpd_sec and tcpd_sec_d else tcpd_sec
    )

    # 5. Cross-check education from TCPD (fill if not already parsed)
    if not profile["education"]["degree"] and row["MyNeta_education"]:
        profile["education"]["category"] = row["MyNeta_education"]

    return profile


def main():
    all_rows = load_csv()
    csv_2022 = [r for r in all_rows if r["Constituency_No"] == "322" and r["Year"] == "2022"]

    profiles = json.loads(PROFILES_IN.read_text(encoding="utf-8"))

    constituency_history = build_constituency_history(all_rows)

    matched = unmatched = 0
    for profile in profiles:
        row = match_row(profile, csv_2022)
        if row:
            enrich_profile(profile, row)
            matched += 1
            print(f"  matched: {profile['personal']['name']} -> {row['Candidate']}")
        else:
            unmatched += 1
            print(f"  NO MATCH: {profile['personal']['name']} ({profile['personal']['party']})")
        # Attach constituency history to every profile
        profile["constituency_history"] = constituency_history

    PROFILES_OUT.write_text(
        json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nDone. matched={matched} unmatched={unmatched}")
    print(f"Constituency history: {len(constituency_history)} elections (1962-2022)")
    print(f"Written to {PROFILES_OUT}")


if __name__ == "__main__":
    main()
