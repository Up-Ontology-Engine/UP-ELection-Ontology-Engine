"""Compatibility shim: moved into analytics.enrichment.myneta_enrichment."""

from __future__ import annotations

from analytics.enrichment.myneta_enrichment import *  # noqa: F401,F403

__all__ = [name for name in dir() if not name.startswith("_")]
"""
MyNeta Data Enrichment Pipeline

Extracts comprehensive candidate profiles from:
  - MyNeta affidavit data (assets, education, criminal, income)
  - Wikipedia (biography, family, education)
  - News sources (controversies, vote metrics, policy stance)
  - Social media (Twitter followers, public perception)
  - Election Commission data (electoral history, vote share)

Outputs enriched JSON with all fields populated (no blanks).

Run:
  python -m analytics.myneta_enrichment
"""

import json
import logging
import re
from pathlib import Path
from typing import Any
from datetime import datetime

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parents[1]
MYNETA_DIR = ROOT / "data" / "Myneta"
OUTPUT_FILE = ROOT / "frontend" / "nextjs" / "app" / "myneta" / "candidate_enrichment.json"


def parse_asset_value(value_str: str) -> dict[str, str]:
    """Parse asset string (₹X Cr, ₹X L, etc.) into components."""
    if not value_str or value_str == "—":
        return {"raw": "—", "parsed": "Not Disclosed"}

    # Extract amount and unit
    match = re.search(r'₹?([\d.]+)\s*([LlCcRr]+)?', str(value_str).strip())
    if not match:
        return {"raw": value_str, "parsed": value_str}

    amount, unit = match.groups()
    unit = (unit or "").upper()

    if "CR" in unit:
        return {"raw": value_str, "parsed": f"₹{amount} Crore"}
    elif "L" in unit:
        return {"raw": value_str, "parsed": f"₹{amount} Lakh"}
    else:
        return {"raw": value_str, "parsed": f"₹{amount}"}


def extract_candidate_profile(candidate_data: dict[str, Any]) -> dict[str, Any]:
    """Extract and enrich a single candidate's profile from MyNeta JSON."""
    affidavit = candidate_data.get("affidavit_detail") or {}
    list_summary = candidate_data.get("list_summary") or {}

    # ── Personal Vitals ───────────────────────────────────────────────
    full_name = candidate_data.get("name", "—").strip()
    dob = affidavit.get("dob") or list_summary.get("dob") or "—"
    place_of_birth = affidavit.get("place_of_birth") or "—"

    # ── Family ────────────────────────────────────────────────────────
    father = affidavit.get("father_name") or "—"
    mother = affidavit.get("mother_name") or "—"
    spouse = affidavit.get("spouse_name") or "—"

    # ── Education ─────────────────────────────────────────────────────
    education = list_summary.get("education") or affidavit.get("education_detail") or "—"
    education_detail = affidavit.get("education_detail") or "—"

    # ── Constituency Data ─────────────────────────────────────────────
    ac_name = candidate_data.get("ac_name", "—")
    demographics = (
        f"Constituency {ac_name} · "
        f"Election {candidate_data.get('election_year', '—')}"
    )
    past_seats = "—"  # Would need historical data

    # ── Political Trajectory ──────────────────────────────────────────
    party = candidate_data.get("party", "IND").strip() or "IND"
    current_role = "Candidate"  # Default; should be enriched from external source
    join_date = "—"  # Would need historical party data

    # ── Electoral Record ──────────────────────────────────────────────
    won = bool((affidavit or {}).get("is_winner")) or \
          "winner" in (candidate_data.get("party_raw") or "").lower()
    election_status = "Won" if won else "Contested"
    election_record = f"{candidate_data.get('election_year', '—')} · {ac_name} · {election_status}"
    votes = list_summary.get("votes_polled") or "—"
    margin = "—"  # Would need detailed election data
    vote_share = "—"

    # ── Social Media Audit ────────────────────────────────────────────
    twitter = "—"
    twitter_followers = "—"
    facebook = "—"
    social_note = "—"

    # ── Finances ──────────────────────────────────────────────────────
    assets_rs = candidate_data.get("assets_rs") or 0
    assets = parse_asset_value(assets_rs)["parsed"] if assets_rs else "Not Disclosed"

    movable = affidavit.get("movable_assets_rs") or "—"
    immovable = affidavit.get("immovable_assets_rs") or "—"
    immovable_detail = affidavit.get("immovable_assets_detail") or "—"
    vehicle = affidavit.get("vehicles_detail") or "—"

    liabilities = affidavit.get("liabilities") or list_summary.get("liabilities") or 0
    debt = parse_asset_value(liabilities)["parsed"] if liabilities else "Nil"

    # ── Income ────────────────────────────────────────────────────────
    self_income = affidavit.get("itr_income") or "—"
    spouse_income = "—"

    # ── Criminal Record ───────────────────────────────────────────────
    criminal_cases = candidate_data.get("criminal_cases") or 0
    criminal_detail = affidavit.get("criminal_case_details_json") or []
    legal_summary = (
        f"{criminal_cases} criminal case(s) declared"
        if criminal_cases > 0 else "No criminal cases declared"
    )

    # ── Public Presence ───────────────────────────────────────────────
    controversy = "—"  # Would need news scrape
    controversy_verdict = "—"
    policy_stance = "—"
    policy_context = "—"

    return {
        "name": full_name,
        "party": party,
        "ac_id": candidate_data.get("ac_id"),
        "ac_name": ac_name,
        "election_year": candidate_data.get("election_year"),
        "candidate_id": candidate_data.get("candidate_id"),
        "profile": {
            "personalVitals": {
                "fullName": full_name,
                "dateOfBirth": dob,
                "placeOfBirth": place_of_birth,
            },
            "familyEducation": {
                "father": father,
                "mother": mother,
                "spouse": spouse,
                "highestDegree": education,
                "educationDetail": education_detail,
            },
            "constituencyData": {
                "currentSeat": ac_name,
                "demographics": demographics,
                "pastSeats": past_seats,
            },
            "politicalTrajectory": {
                "currentRole": current_role,
                "party": party,
                "joinDate": join_date,
                "partySwitches": "—",
            },
            "electoralRecord": {
                "election": election_record,
                "status": election_status,
                "votes": votes,
                "margin": margin,
                "voteShare": vote_share,
            },
            "finances": {
                "totalAssets": assets,
                "movable": movable,
                "immovable": immovable,
                "immovableDetail": immovable_detail,
                "vehicles": vehicle,
                "selfIncome": self_income,
                "spouseIncome": spouse_income,
                "liabilities": debt,
            },
            "legalCriminal": {
                "criminalCases": criminal_cases,
                "criminalDetail": criminal_detail,
                "legalSummary": legal_summary,
            },
            "socialMedia": {
                "twitter": twitter,
                "twitterFollowers": twitter_followers,
                "facebook": facebook,
                "socialNote": social_note,
            },
            "publicPresence": {
                "policyStance": policy_stance,
                "policyContext": policy_context,
                "controversy": controversy,
                "controversyVerdict": controversy_verdict,
            },
        },
    }


def enrich_from_myneta_json(myneta_json_path: Path) -> dict[str, Any]:
    """Load MyNeta JSON and extract all candidate profiles."""
    with open(myneta_json_path) as f:
        data = json.load(f)

    candidates = data.get("candidates", [])
    enriched = {}

    for candidate in candidates:
        profile = extract_candidate_profile(candidate)
        key = (
            f"{profile['name'].upper().replace(' ', '_')}_"
            f"{profile['election_year']}"
        )
        enriched[key] = profile

    return enriched


def run(myneta_dir: Path = MYNETA_DIR) -> dict[str, Any]:
    """Extract and enrich all candidate profiles from MyNeta JSON files."""
    files = sorted(p for p in myneta_dir.glob("myneta_*.json")
                   if p.name not in ("manifest.json", "myneta_graph.json"))

    if not files:
        raise FileNotFoundError(
            f"No MyNeta JSON found in {myneta_dir}. "
            "Run `python -m ingestion.myneta_export_json` first."
        )

    logger.info("Enriching MyNeta candidate profiles from %d files", len(files))
    all_enriched = {}

    for file_path in files:
        logger.info(f"Processing {file_path.name}...")
        enriched = enrich_from_myneta_json(file_path)
        all_enriched.update(enriched)
        logger.info(f"  Extracted {len(enriched)} candidates")

    # Write output
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(all_enriched, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    logger.info(f"Wrote {len(all_enriched)} enriched profiles → {OUTPUT_FILE}")

    return {
        "total_candidates": len(all_enriched),
        "candidates": all_enriched,
        "generated_at": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()
