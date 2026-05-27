"""
Ingestion: Electoral Roll PDFs → booth_master (via digital-democracy-pipeline)

Uses the digital-democracy-pipeline (ddp) package to:
  1. Run Sarvam OCR on image-based Hindi electoral roll PDFs
  2. Extract ElectoralRollRecord objects (including भाग संख्या = part_no)
  3. Aggregate by part_no → booth-level voter demographics
  4. Update booth_master with real Part-No-based booth_ids

WHY THIS IS CRITICAL:
  The XLSX conversion of electoral rolls had Part No missing (all empty).
  The original Hindi PDFs DO contain "भाग संख्या" (part_no).
  Sarvam OCR + electoral_roll.py extracts it → real booth_id keys like
  "GKP_322_045" that connect electoral data to every other table.

Source PDFs (image-based Hindi script, AC 322):
  data/data/Raw file/2026-EROLLGEN-S24-322-SIR-FinalRoll-Revision1-HIN-2-WI-3-10 (2).pdf
  data/data/Raw file/2026-EROLLGEN-S24-322-SIR-FinalRoll-Revision1-HIN-2-WI-3-10 (3).pdf

Requires:
  SARVAM_API_KEY env var  (OCR costs ~₹1.50/page, one-time)
  pip install -e 'digital-democracy-pipeline/[sarvam]'
  pip install deep-translator

Run:
  python -m ingestion.ddp_electoral_roll
  python -m ingestion.ddp_electoral_roll --pdf "path/to/roll.pdf" --ac 322
  python -m ingestion.ddp_electoral_roll --dry-run   (OCR + extract, no DB write)
"""

from __future__ import annotations

import argparse
import logging
import os
import re
from collections import defaultdict
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parents[2] / "data" / "data" / "Raw file"
RUNS_DIR = Path(__file__).parents[2] / "data" / "ddp_runs"

ELECTORAL_ROLL_PDFS = [
    (DATA_DIR / "2026-EROLLGEN-S24-322-SIR-FinalRoll-Revision1-HIN-2-WI-3-10 (2).pdf", 322),
    (DATA_DIR / "2026-EROLLGEN-S24-322-SIR-FinalRoll-Revision1-HIN-2-WI-3-10 (3).pdf", 322),
]


def _ac_from_filename(pdf_path: Path) -> int:
    m = re.search(r"S24-(\d+)-", pdf_path.name)
    if m:
        return int(m.group(1))
    raise ValueError(f"Cannot infer AC number from filename: {pdf_path.name}")


def extract_records_from_pdf(pdf_path: Path, out_dir: Path) -> list:
    """
    Full ddp pipeline: PDF → Sarvam OCR → electoral_roll extraction → ElectoralRollRecord list.
    Writes Excel outputs to out_dir.
    Returns list of ElectoralRollRecord objects with part_no, gender, age fields.
    """
    from digital_democracy_pipeline.detector import detect_upload
    from digital_democracy_pipeline.electoral_roll import (
        LocalGoogleTranslator,
        build_electoral_outputs,
    )
    from digital_democracy_pipeline.normalizers import normalize_mediaset_pages
    from digital_democracy_pipeline.sarvam import SarvamDocumentIntelligenceExtractor

    api_key = os.environ.get("SARVAM_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "SARVAM_API_KEY not set.\n"
            "Get a key at https://dashboard.sarvam.ai and export SARVAM_API_KEY=sk_..."
        )

    logger.info("Step 1/3 — Sarvam OCR: %s", pdf_path.name)
    extractor = SarvamDocumentIntelligenceExtractor(
        api_key=api_key,
        language="hi-IN",
        output_format="md",
    )
    pages = extractor.extract_pages(pdf_path)
    logger.info("  OCR complete: %d pages extracted", len(pages))

    logger.info("Step 2/3 — Normalise pages")
    manifest = detect_upload(pdf_path)
    rows = normalize_mediaset_pages(manifest, pages)
    logger.info("  Normalised: %d rows", len(rows))

    logger.info("Step 3/3 — Extract electoral roll records + translate")
    out_dir.mkdir(parents=True, exist_ok=True)
    translator = LocalGoogleTranslator()
    _, english_records, _ = build_electoral_outputs(
        manifest=manifest,
        rows=rows,
        out_dir=out_dir,
        translator=translator,
    )

    logger.info(
        "Extracted %d ElectoralRollRecord objects from %s", len(english_records), pdf_path.name
    )
    return english_records


def aggregate_by_booth(records: list, ac_no: int) -> dict[str, dict]:
    """
    Group ElectoralRollRecord objects by part_no → per-booth demographic counts.
    Returns {booth_id: {male_voters, female_voters, other_voters, total_voters, age_*}}
    """
    booths: dict[str, dict] = defaultdict(
        lambda: {
            "male_voters": 0,
            "female_voters": 0,
            "other_voters": 0,
            "total_voters": 0,
            "age_18_25": 0,
            "age_26_40": 0,
            "age_40_60": 0,
            "age_60_plus": 0,
        }
    )

    skipped = 0
    for rec in records:
        part_raw = str(rec.part_no or "").strip()
        digits = re.sub(r"[^\d]", "", part_raw)
        if not digits:
            skipped += 1
            continue

        part_no = int(digits)
        booth_id = f"GKP_{ac_no}_{part_no:03d}"
        b = booths[booth_id]

        gender = str(rec.gender or "").strip().upper()
        if gender in ("M", "MALE"):
            b["male_voters"] += 1
        elif gender in ("F", "FEMALE", "WOMAN"):
            b["female_voters"] += 1
        else:
            b["other_voters"] += 1
        b["total_voters"] += 1

        try:
            age = int(re.sub(r"[^\d]", "", str(rec.age or "0")) or 0)
            if 18 <= age <= 25:
                b["age_18_25"] += 1
            elif 26 <= age <= 40:
                b["age_26_40"] += 1
            elif 41 <= age <= 60:
                b["age_40_60"] += 1
            elif age > 60:
                b["age_60_plus"] += 1
        except (ValueError, TypeError):
            pass

    if skipped:
        logger.warning("%d records had no parseable part_no — skipped", skipped)

    logger.info(
        "Aggregated %d unique booths from %d valid records (AC %d)",
        len(booths),
        len(records) - skipped,
        ac_no,
    )
    return dict(booths)


def load_booths_to_postgres(booth_data: dict[str, dict], ac_no: int, engine: sa.Engine) -> int:
    """Upsert booth_master with voter demographics from PDF extraction using batch operations."""
    ac_id = f"GKP_{ac_no}"
    bind_params = []
    for booth_id, d in booth_data.items():
        part_no = int(booth_id.split("_")[-1])
        bind_params.append(
            {
                "booth_id": booth_id,
                "ac_id": ac_id,
                "part_no": part_no,
                "male": d["male_voters"],
                "female": d["female_voters"],
                "other": d["other_voters"],
                "total": d["total_voters"],
            }
        )

    if not bind_params:
        return 0

    with engine.connect() as conn:
        conn.execute(
            text("""
            INSERT INTO booth_master
                (booth_id, ac_id, booth_number,
                 male_voters, female_voters, other_voters, total_voters)
            VALUES
                (:booth_id, :ac_id, :part_no,
                 :male, :female, :other, :total)
            ON CONFLICT (booth_id) DO UPDATE SET
                male_voters   = EXCLUDED.male_voters,
                female_voters = EXCLUDED.female_voters,
                other_voters  = EXCLUDED.other_voters,
                total_voters  = EXCLUDED.total_voters,
                updated_at    = NOW()
        """),
            bind_params,
        )
        conn.commit()

    logger.info(
        "Upserted %d booths into booth_master (AC %d) via batch upsert", len(bind_params), ac_no
    )
    return len(bind_params)


def process_pdf(
    pdf_path: Path, ac_no: int, engine: sa.Engine | None = None, dry_run: bool = False
) -> dict[str, dict]:
    run_dir = RUNS_DIR / pdf_path.stem
    records = extract_records_from_pdf(pdf_path, run_dir)
    booths = aggregate_by_booth(records, ac_no)

    if dry_run:
        logger.info("[DRY RUN] %d booths — sample:", len(booths))
        for bid, d in list(booths.items())[:5]:
            logger.info(
                "  %s  male=%d  female=%d  total=%d",
                bid,
                d["male_voters"],
                d["female_voters"],
                d["total_voters"],
            )
    elif engine:
        load_booths_to_postgres(booths, ac_no, engine)

    return booths


def run(pdf_paths: list[tuple[Path, int]] | None = None, dry_run: bool = False):
    engine = None if dry_run else sa.create_engine(os.environ["POSTGRES_URL"])
    targets = pdf_paths or [(p, ac) for p, ac in ELECTORAL_ROLL_PDFS if p.exists()]

    if not targets:
        logger.error("No electoral roll PDFs found in %s", DATA_DIR)
        return {}

    import concurrent.futures

    all_booths: dict[str, dict] = {}

    # Process PDFs in parallel since OCR extraction makes network-bound HTTP requests
    max_workers = min(len(targets), 4)
    logger.info("Processing %d PDFs in parallel (max_workers=%d)", len(targets), max_workers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_pdf, pdf_path, ac_no, engine, dry_run): (pdf_path, ac_no)
            for pdf_path, ac_no in targets
            if pdf_path.exists()
        }
        for future in concurrent.futures.as_completed(futures):
            pdf_path, ac_no = futures[future]
            try:
                booths = future.result()
                all_booths.update(booths)
            except Exception as e:
                logger.error("Failed to process PDF %s: %s", pdf_path.name, e, exc_info=True)

    logger.info("Done: %d total booths processed across all PDFs", len(all_booths))
    return all_booths


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Process electoral roll PDFs via Sarvam OCR")
    p.add_argument("--pdf", default=None, help="Path to single PDF (overrides defaults)")
    p.add_argument("--ac", type=int, default=None, help="AC number (e.g. 322)")
    p.add_argument("--dry-run", action="store_true", help="OCR + extract, no DB write")
    args = p.parse_args()

    if args.pdf:
        pdf = Path(args.pdf)
        ac = args.ac or _ac_from_filename(pdf)
        run([(pdf, ac)], dry_run=args.dry_run)
    else:
        run(dry_run=args.dry_run)
