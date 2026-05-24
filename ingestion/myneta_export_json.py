"""
Export the MyNeta pipeline output to JSON (no Postgres required).

Runs the same three scrape passes as ``ingestion.myneta_candidates`` —
list → affidavit detail → expense — but instead of upserting into Postgres,
combines everything per candidate and writes structured JSON files into the
``data/Myneta/`` folder.

For every configured constituency that has a verified ``constituency_id``
(see ``ASSEMBLY_CONSTITUENCIES`` / ``LOK_SABHA`` in ``myneta_candidates``) it
writes one file ``data/Myneta/myneta_<ac_id>_<year>.json`` plus a top-level
``data/Myneta/manifest.json`` summarising the run.

Reuses the scraping logic verbatim from ``myneta_candidates`` — this module
only orchestrates and serialises; it does not re-implement parsing.

Run:
    # All configured constituencies, all passes:
    python -m ingestion.myneta_export_json

    # Just one constituency / fewer passes / quicker:
    python -m ingestion.myneta_export_json --ac 322 --year 2022
    python -m ingestion.myneta_export_json --ls 520
    python -m ingestion.myneta_export_json --ac 322 --pass list --pass detail
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ingestion.myneta_candidates import (
    ASSEMBLY_CONSTITUENCIES,
    LOK_SABHA,
    _normalise_party,
    _slugify,
    scrape_affidavit_detail,
    scrape_constituency_list,
    scrape_expense_page,
)

logger = logging.getLogger(__name__)

OUT_DIR = Path(__file__).parents[1] / "data" / "Myneta"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def export_constituency(
    ac_id: str,
    ac_name: str,
    election_folder: str,
    constituency_id: int,
    election_year: int,
    passes: list[str],
) -> dict[str, Any]:
    """Scrape one constituency across the requested passes and return a JSON-ready dict."""
    logger.info("Scraping %s %s (%s, constituency_id=%d)", ac_id, election_year, ac_name, constituency_id)
    candidates = scrape_constituency_list(constituency_id, election_folder)

    records: list[dict[str, Any]] = []
    for c in candidates:
        rec: dict[str, Any] = {
            "candidate_id": _slugify(c["name"], election_year),
            "name": c["name"],
            "party": _normalise_party(c.get("party_raw", "")),
            "party_raw": c.get("party_raw"),
            "ac_id": ac_id,
            "ac_name": ac_name,
            "election_year": election_year,
            "source_candidate_id": c.get("source_candidate_id"),
            "detail_url": c.get("detail_url"),
            "list_summary": {
                "education": c.get("education"),
                "age": c.get("age"),
                "criminal_cases": c.get("criminal_cases"),
                "total_assets": c.get("total_assets"),
                "liabilities": c.get("liabilities"),
            },
        }

        src = c.get("source_candidate_id")
        if src and "detail" in passes:
            rec["affidavit_detail"] = scrape_affidavit_detail(int(src), election_folder)
            time.sleep(0.3)
        if src and "expense" in passes:
            rec["expense"] = scrape_expense_page(int(src), election_folder)
            time.sleep(0.2)

        records.append(rec)

    return {
        "ac_id": ac_id,
        "ac_name": ac_name,
        "election_year": election_year,
        "election_folder": election_folder,
        "constituency_id": constituency_id,
        "source": "myneta",
        "passes": passes,
        "scraped_at": _now_iso(),
        "candidate_count": len(records),
        "candidates": records,
    }


def _targets(ac: int | None, ls: int | None, year: int | None) -> list[tuple[str, str, str, int, int]]:
    """Resolve (ac_id, ac_name, election_folder, constituency_id, year) tuples to scrape.

    Only constituencies with a verified (non-None) constituency_id are included.
    """
    out: list[tuple[str, str, str, int, int]] = []

    if ls is not None:
        if ls not in LOK_SABHA:
            raise ValueError(f"LS constituency_id {ls} not in LOK_SABHA map")
        ac_id, name, folder, cid = LOK_SABHA[ls]
        yr = int("".join(ch for ch in folder if ch.isdigit())[-4:])
        if cid is not None:
            out.append((ac_id, name, folder, cid, yr))
        return out

    if ac is not None:
        keys = [(ac, year)] if year is not None else [k for k in ASSEMBLY_CONSTITUENCIES if k[0] == ac]
        for key in keys:
            if key not in ASSEMBLY_CONSTITUENCIES:
                raise ValueError(f"AC {key} not in ASSEMBLY_CONSTITUENCIES")
            ac_id, name, folder, cid = ASSEMBLY_CONSTITUENCIES[key]
            if cid is not None:
                out.append((ac_id, name, folder, cid, key[1]))
        return out

    # Default: every configured constituency with a verified constituency_id.
    for (ac_no, yr), (ac_id, name, folder, cid) in ASSEMBLY_CONSTITUENCIES.items():
        if cid is not None:
            out.append((ac_id, name, folder, cid, yr))
    for ls_no, (ac_id, name, folder, cid) in LOK_SABHA.items():
        if cid is not None:
            yr = int("".join(ch for ch in folder if ch.isdigit())[-4:])
            out.append((ac_id, name, folder, cid, yr))
    return out


def run(
    ac: int | None = None,
    ls: int | None = None,
    year: int | None = None,
    passes: list[str] | None = None,
    out_dir: Path = OUT_DIR,
) -> dict[str, Any]:
    passes = passes or ["list", "detail", "expense"]
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = _targets(ac, ls, year)
    if not targets:
        logger.error("No scrapeable targets (no verified constituency_id for the given filters).")
        return {}

    manifest_files: list[dict[str, Any]] = []
    for ac_id, name, folder, cid, yr in targets:
        data = export_constituency(ac_id, name, folder, cid, yr, passes)
        fname = f"myneta_{ac_id}_{yr}.json"
        path = out_dir / fname
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Wrote %d candidates → %s", data["candidate_count"], path)
        manifest_files.append({
            "file": fname,
            "ac_id": ac_id,
            "ac_name": name,
            "election_year": yr,
            "constituency_id": cid,
            "candidate_count": data["candidate_count"],
        })

    manifest = {
        "source": "myneta",
        "generated_at": _now_iso(),
        "passes": passes,
        "constituencies": manifest_files,
        "total_candidates": sum(f["candidate_count"] for f in manifest_files),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Manifest written → %s (%d files, %d candidates)",
                out_dir / "manifest.json", len(manifest_files), manifest["total_candidates"])
    return manifest


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Export MyNeta pipeline data to JSON in data/Myneta/")
    p.add_argument("--ac", type=int, default=None, help="Vidhan Sabha AC number (e.g. 322)")
    p.add_argument("--ls", type=int, default=None, help="Lok Sabha constituency_id (e.g. 520)")
    p.add_argument("--year", type=int, default=None, help="Election year filter for --ac")
    p.add_argument("--pass", dest="passes", action="append",
                   choices=["list", "detail", "expense"],
                   help="Which pass(es) to run (default: all three)")
    p.add_argument("--out", type=Path, default=OUT_DIR, help="Output folder (default: data/Myneta)")
    args = p.parse_args()
    run(ac=args.ac, ls=args.ls, year=args.year, passes=args.passes, out_dir=args.out)
