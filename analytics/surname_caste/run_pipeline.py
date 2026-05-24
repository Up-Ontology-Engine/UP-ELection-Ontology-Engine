"""
run_pipeline.py
================
Master orchestrator for the Surname–Caste Electoral Influence pipeline.

Usage
-----
# Full pipeline for AC 322
python -m analytics.surname_caste.run_pipeline --ac 322

# Skip LLM (use cache + bootstrap only)
python -m analytics.surname_caste.run_pipeline --ac 322 --no-llm

# Force recompute all stages
python -m analytics.surname_caste.run_pipeline --ac 322 --force

# Linkage report only (no caste analysis)
python -m analytics.surname_caste.run_pipeline --ac 322 --linkage-only

# Dry run (parse only, no writes)
python -m analytics.surname_caste.run_pipeline --ac 322 --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
TRANSFORMED = ROOT / "data" / "transformed"


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )


def run(
    ac_number: int = 322,
    *,
    force: bool = False,
    use_llm: bool = True,
    linkage_only: bool = False,
    dry_run: bool = False,
    include_suspect: bool = True,
) -> dict:
    """
    Execute the full pipeline. Returns a summary dict.
    """
    t0 = time.time()
    summary = {"ac": ac_number, "stages": {}}

    # ── Stage 1: Parse voter roll ────────────────────────────────────────────
    log.info("=" * 60)
    log.info("STAGE 1: Parsing voter roll")
    log.info("=" * 60)
    from analytics.surname_caste.etl.parse_voter_roll import parse_voter_roll

    voter_roll = parse_voter_roll(force=force)
    summary["stages"]["voter_roll"] = {
        "total_voters": len(voter_roll),
        "parts": voter_roll["part_number"].nunique(),
    }
    log.info("✓ Voter roll: %d voters across %d parts", len(voter_roll), voter_roll["part_number"].nunique())

    # ── Stage 2: Parse Form 20 ───────────────────────────────────────────────
    log.info("=" * 60)
    log.info("STAGE 2: Parsing Form 20 results")
    log.info("=" * 60)
    from analytics.surname_caste.etl.parse_form20 import parse_form20_ac322, parse_form20_named

    form20_322 = parse_form20_ac322(force=force)
    form20_named = parse_form20_named(force=force)
    summary["stages"]["form20"] = {
        "ac322_rows": len(form20_322),
        "ac322_stations": form20_322["ps_number"].nunique() if len(form20_322) else 0,
        "named_rows": len(form20_named),
    }
    log.info("✓ Form20 AC322: %d rows, %d stations", len(form20_322), form20_322["ps_number"].nunique())
    log.info("✓ Form20 named ACs: %d rows", len(form20_named))

    # ── Stage 3: Parse candidates ────────────────────────────────────────────
    log.info("=" * 60)
    log.info("STAGE 3: Parsing candidate records")
    log.info("=" * 60)
    from analytics.surname_caste.etl.parse_candidates import parse_candidates

    candidates = parse_candidates(force=force)
    summary["stages"]["candidates"] = {"total": len(candidates)}
    log.info("✓ Candidates: %d records", len(candidates))

    # ── Stage 4: Booth linkage ───────────────────────────────────────────────
    log.info("=" * 60)
    log.info("STAGE 4: Building booth linkage map")
    log.info("=" * 60)
    from analytics.surname_caste.etl.booth_linker import build_linkage_map

    linkage = build_linkage_map(voter_roll, form20_322, ac_number=ac_number, force=force)
    status_counts = linkage["match_status"].value_counts().to_dict()
    summary["stages"]["linkage"] = status_counts
    log.info("✓ Linkage: %s", status_counts)

    if linkage_only:
        log.info("--linkage-only flag set, stopping here.")
        _print_linkage_report(linkage)
        return summary

    if dry_run:
        log.info("--dry-run flag set, stopping after linkage.")
        return summary

    # ── Stage 5: Surname extraction ──────────────────────────────────────────
    log.info("=" * 60)
    log.info("STAGE 5: Extracting surnames")
    log.info("=" * 60)
    from analytics.surname_caste.surname_extractor import extract_surnames

    vr_with_surnames = extract_surnames(voter_roll)
    conf_dist = vr_with_surnames["surname_confidence"].value_counts().to_dict()
    n_unknown = (vr_with_surnames["surname"] == "UNKNOWN").sum()
    summary["stages"]["surname_extraction"] = {
        "confidence_dist": conf_dist,
        "unknown": int(n_unknown),
    }
    log.info("✓ Surnames extracted. Confidence: %s | Unknown: %d", conf_dist, n_unknown)

    # ── Stage 6: Caste mapping ───────────────────────────────────────────────
    log.info("=" * 60)
    log.info("STAGE 6: Mapping surnames to caste groups")
    log.info("=" * 60)
    from analytics.surname_caste.caste_mapper import CasteMapper, initialise_cache

    initialise_cache()
    mapper = CasteMapper(use_llm=use_llm)

    unique_surnames = vr_with_surnames["surname"].dropna().unique().tolist()
    log.info("Classifying %d unique surnames…", len(unique_surnames))
    mapper.classify_batch(unique_surnames)

    # Apply RapidFuzz normalisation against known cache keys
    try:
        from analytics.surname_caste.surname_extractor import normalise_surnames_against_map
        vr_with_surnames = normalise_surnames_against_map(
            vr_with_surnames, mapper._cache, threshold=85
        )
        effective_col = "surname_normalised"
    except Exception:
        effective_col = "surname"

    vr_enriched = mapper.enrich_dataframe(vr_with_surnames, surname_col=effective_col)

    # Save enriched voter roll
    enriched_path = TRANSFORMED / "voter_roll_normalised_caste.parquet"
    vr_enriched.to_parquet(enriched_path, index=False)
    log.info("✓ Enriched voter roll saved → %s", enriched_path)

    cache_stats = mapper.cache_stats()
    summary["stages"]["caste_mapping"] = cache_stats
    log.info("✓ Caste mapping done. Cache: %s", cache_stats)

    # ── Stage 7: Aggregation ─────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("STAGE 7: Aggregating caste composition per booth")
    log.info("=" * 60)
    from analytics.surname_caste.aggregator import build_caste_booth_analysis

    analysis_df = build_caste_booth_analysis(
        voter_roll_path=enriched_path,
        include_suspect=include_suspect,
        force=force,
    )
    summary["stages"]["aggregation"] = {
        "booths": len(analysis_df),
        "caste_groups": sum(1 for c in analysis_df.columns if c.startswith("caste_share_")),
        "parties": sum(1 for c in analysis_df.columns if c.startswith("party_share_")),
    }
    log.info(
        "✓ Aggregation: %d booths, %d caste groups, %d parties",
        len(analysis_df),
        summary["stages"]["aggregation"]["caste_groups"],
        summary["stages"]["aggregation"]["parties"],
    )

    # ── Stage 8: Influence scoring ───────────────────────────────────────────
    log.info("=" * 60)
    log.info("STAGE 8: Computing influence scores")
    log.info("=" * 60)
    from analytics.surname_caste.influence_scorer import (
        compute_influence_scores,
        top_influential_castes,
    )

    scores = compute_influence_scores(
        analysis_df,
        candidates,
        ac_number=ac_number,
        force=force,
    )
    top = top_influential_castes(scores, ac_key=f"ac_{ac_number}", n=10)
    summary["stages"]["influence_scores"] = {"top_castes": [r["caste"] for r in top[:5]]}
    log.info("✓ Influence scores computed.")

    # ── Final summary ─────────────────────────────────────────────────────────
    elapsed = round(time.time() - t0, 1)
    summary["elapsed_seconds"] = elapsed

    log.info("=" * 60)
    log.info("PIPELINE COMPLETE in %.1fs", elapsed)
    log.info("=" * 60)
    _print_top_castes(top)

    return summary


def _print_linkage_report(linkage) -> None:
    print("\n" + "=" * 70)
    print("BOOTH LINKAGE REPORT")
    print("=" * 70)
    print(f"{'Part#':>6}  {'VR Count':>9}  {'F20 Electors':>13}  {'Delta%':>7}  {'Status'}")
    print("-" * 70)
    for _, row in linkage.sort_values("part_number").iterrows():
        delta = f"{row['delta_pct']:.1%}" if row.get("delta_pct") is not None else "N/A"
        vr = str(row.get("voter_roll_count") or "N/A")
        f20 = str(row.get("form20_electors") or "N/A")
        print(f"{int(row['part_number']):>6}  {vr:>9}  {f20:>13}  {delta:>7}  {row['match_status']}")
    print("=" * 70)
    counts = linkage["match_status"].value_counts().to_dict()
    for status, cnt in sorted(counts.items()):
        print(f"  {status}: {cnt}")


def _print_top_castes(top: list[dict]) -> None:
    print("\n" + "=" * 70)
    print("TOP INFLUENTIAL CASTE GROUPS")
    print("=" * 70)
    print(f"{'Caste':20s}  {'Pop%':>6}  {'DomParty':>10}  {'WinPct':>7}  {'Swing':>8}  {'BestR':>6}")
    print("-" * 70)
    for row in top:
        pop = f"{row['population_share']:.1%}" if row.get("population_share") else "N/A"
        dom = row.get("dominant_party") or "N/A"
        wpc = f"{row['dominant_party_win_pct']:.0%}" if row.get("dominant_party_win_pct") else "N/A"
        swg = row.get("swing_potential") or "N/A"
        br  = f"{row['best_corr_r']:.2f}" if row.get("best_corr_r") else "N/A"
        print(f"{row['caste']:20s}  {pop:>6}  {dom:>10}  {wpc:>7}  {swg:>8}  {br:>6}")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Surname–Caste Electoral Influence Pipeline"
    )
    parser.add_argument("--ac", type=int, default=322, help="Assembly constituency number")
    parser.add_argument("--force", action="store_true", help="Recompute all cached stages")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM; use bootstrap cache only")
    parser.add_argument("--linkage-only", action="store_true", help="Only run linkage reconciliation")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, no writes")
    parser.add_argument("--include-suspect", action="store_true", default=True,
                        help="Include SUSPECT-status booths in analysis")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    setup_logging(args.verbose)

    try:
        summary = run(
            ac_number=args.ac,
            force=args.force,
            use_llm=not args.no_llm,
            linkage_only=args.linkage_only,
            dry_run=args.dry_run,
            include_suspect=args.include_suspect,
        )
        import json
        print("\nPIPELINE SUMMARY:")
        print(json.dumps(summary, indent=2, default=str))
    except Exception as exc:
        log.exception("Pipeline failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
