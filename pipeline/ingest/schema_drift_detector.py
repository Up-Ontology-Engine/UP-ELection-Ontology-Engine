"""
ECI / MyNeta affidavit schema drift detector.

Monitors government portal HTML structures for unexpected changes that would
silently break parsing routines.  Designed to run as a daily cron or CI job.

Checks performed:
  1. MyNeta candidate list table — required column headers present.
  2. MyNeta affidavit detail page — required h3 section headings present.
  3. DOM selector availability (presence of key CSS selectors / tag patterns).
  4. Validates a Pydantic model for parsed candidate rows.

On drift detection, logs a critical-level message and writes a report to
data/raw/drift_reports/ for alerting integration.

Usage:
    python -m ingestion.schema_drift_detector
    python -m ingestion.schema_drift_detector --ac 322 --year 2022
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

_ROOT   = Path(__file__).resolve().parents[1]
_REPORT = _ROOT / "data" / "raw" / "drift_reports"
_REPORT.mkdir(parents=True, exist_ok=True)

# ── Expected schema signatures ────────────────────────────────────────────────

# Column header keywords that must appear in the MyNeta candidate list table.
REQUIRED_LIST_HEADERS = frozenset([
    "candidate", "party", "criminal", "assets", "education",
])

# h3 section headings that must appear on a MyNeta affidavit detail page.
REQUIRED_AFFIDAVIT_SECTIONS = frozenset([
    "movable asset",
    "immovable asset",
    "liabilit",     # prefix match — "Liabilities" or "Liability"
])

# ECI booth result page expected table structure (at least these columns).
REQUIRED_ECI_RESULT_COLUMNS = frozenset([
    "booth", "candidate", "party", "votes",
])


# ── Pydantic validator for parsed candidate rows ──────────────────────────────

class ParsedCandidateRow(BaseModel):
    """Validate a single row from the MyNeta constituency list scrape."""
    name:             str
    party_raw:        Optional[str] = None
    education:        Optional[str] = None
    age:              Optional[int] = None
    criminal_cases:   int = 0
    total_assets:     int = 0
    liabilities:      int = 0
    source_candidate_id: Optional[int] = None

    class Config:
        extra = "allow"   # forward-compat: extra fields don't error


def validate_candidate_rows(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Validate parsed candidate rows against the schema.

    Returns:
        (valid_rows, invalid_rows) — invalid rows include a 'validation_error' key.
    """
    valid, invalid = [], []
    for row in rows:
        try:
            ParsedCandidateRow.model_validate(row)
            valid.append(row)
        except ValidationError as exc:
            invalid.append({**row, "validation_error": exc.errors()})
    return valid, invalid


# ── DOM structure checks ──────────────────────────────────────────────────────

def _check_list_page(html: str, source_url: str) -> dict:
    """Verify MyNeta candidate list page has expected headers and table."""
    issues = []

    # Must have a <table>
    if "<table" not in html.lower():
        issues.append("No <table> element found on candidate list page")

    # Check required column keywords
    html_lower = html.lower()
    missing_headers = [h for h in REQUIRED_LIST_HEADERS if h not in html_lower]
    if missing_headers:
        issues.append(f"Missing expected column headers: {missing_headers}")

    # Must have candidate.php links (detail page anchors)
    if "candidate.php" not in html:
        issues.append("No candidate.php links found — candidate roster may have moved")

    return {
        "check": "list_page",
        "url":   source_url,
        "ok":    len(issues) == 0,
        "issues": issues,
    }


def _check_affidavit_page(html: str, candidate_id: int, source_url: str) -> dict:
    """Verify MyNeta affidavit detail page has expected section headings."""
    issues = []
    html_lower = html.lower()

    missing = [s for s in REQUIRED_AFFIDAVIT_SECTIONS if s not in html_lower]
    if missing:
        issues.append(f"Missing required h3 sections: {missing}")

    # Should have at least one <table>
    if html_lower.count("<table") < 2:
        issues.append("Fewer than 2 tables found — affidavit structure may have changed")

    return {
        "check":        "affidavit_page",
        "candidate_id": candidate_id,
        "url":          source_url,
        "ok":           len(issues) == 0,
        "issues":       issues,
    }


def _check_eci_result_page(html: str, source_url: str) -> dict:
    """Verify ECI booth result page has expected column headers."""
    issues = []
    html_lower = html.lower()

    missing = [c for c in REQUIRED_ECI_RESULT_COLUMNS if c not in html_lower]
    if missing:
        issues.append(f"Missing ECI result columns: {missing}")

    if "<table" not in html_lower:
        issues.append("No <table> on ECI result page — DOM may have changed to JS-rendered")

    return {
        "check":  "eci_result_page",
        "url":    source_url,
        "ok":     len(issues) == 0,
        "issues": issues,
    }


# ── HTTP fetch helper (same as myneta_candidates._get but standalone) ─────────

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _fetch(url: str, timeout: int = 20) -> str | None:
    try:
        import urllib.request
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        # Decompress if gzip
        if raw[:2] == b"\x1f\x8b":
            import gzip
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", errors="replace")
    except Exception as exc:
        logger.warning("[drift] Fetch failed %s: %s", url, exc)
        return None


# ── Orchestrator ──────────────────────────────────────────────────────────────

def run_drift_check(
    ac_no: int = 322,
    election_year: int = 2022,
    constituency_id: int = 186,
    sample_candidate_id: int = 3801,
) -> dict:
    """
    Run all schema drift checks for one AC.

    Returns a structured report dict.  Critical issues are logged at ERROR level.
    """
    results = []
    drift_detected = False

    base = "https://www.myneta.info"
    folder = f"uttarpradesh{election_year}"

    # 1. MyNeta candidate list
    list_url = f"{base}/{folder}/index.php?action=show_candidates&constituency_id={constituency_id}"
    html = _fetch(list_url)
    if html:
        r = _check_list_page(html, list_url)
        results.append(r)
        if not r["ok"]:
            drift_detected = True
            logger.error("[drift] LIST PAGE DRIFT: %s", r["issues"])
    else:
        results.append({"check": "list_page", "url": list_url, "ok": False, "issues": ["fetch_failed"]})
        drift_detected = True
    time.sleep(1.0)

    # 2. MyNeta affidavit detail (sample candidate)
    detail_url = f"{base}/{folder}/candidate.php?candidate_id={sample_candidate_id}"
    html = _fetch(detail_url)
    if html:
        r = _check_affidavit_page(html, sample_candidate_id, detail_url)
        results.append(r)
        if not r["ok"]:
            drift_detected = True
            logger.error("[drift] AFFIDAVIT PAGE DRIFT: %s", r["issues"])
    else:
        results.append({"check": "affidavit_page", "ok": False, "issues": ["fetch_failed"]})
        drift_detected = True
    time.sleep(1.0)

    # 3. ECI result page (static URL — check annually)
    eci_url = f"https://results.eci.gov.in/AcResultGenJune2024/candidateswise-S24{ac_no}.htm"
    html = _fetch(eci_url)
    if html:
        r = _check_eci_result_page(html, eci_url)
        results.append(r)
        if not r["ok"]:
            drift_detected = True
            logger.warning("[drift] ECI RESULT PAGE DRIFT (non-critical): %s", r["issues"])
    # ECI drift is non-critical since results are static

    report = {
        "checked_at":     datetime.now(timezone.utc).isoformat(),
        "ac_no":          ac_no,
        "election_year":  election_year,
        "drift_detected": drift_detected,
        "checks":         results,
    }

    # Save report
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = _REPORT / f"drift_{ac_no}_{ts}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("[drift] Report saved: %s (drift=%s)", report_path, drift_detected)

    if drift_detected:
        logger.critical(
            "[drift] SCHEMA DRIFT DETECTED for AC %d/%d — check %s for details",
            ac_no, election_year, report_path,
        )

    return report


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="ECI/MyNeta schema drift detector")
    parser.add_argument("--ac",   type=int, default=322,  help="AC number (default 322)")
    parser.add_argument("--year", type=int, default=2022, help="Election year (default 2022)")
    args = parser.parse_args()

    report = run_drift_check(ac_no=args.ac, election_year=args.year)
    print(f"\nDrift detected: {report['drift_detected']}")
    for c in report["checks"]:
        status = "✓" if c["ok"] else "✗"
        print(f"  {status} {c['check']}: {c.get('issues', [])}")
