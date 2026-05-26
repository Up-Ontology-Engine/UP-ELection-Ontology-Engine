"""
Master feature ingestion — PoolBoothData_JSON → every DB table.

Fills (in order):
  1. booth_master       — polling_station_name, locality_hint from section data
  2. ac_demographics    — real 114,326-voter gender + age breakdown
  3. data_quality_metrics — per-booth EPIC/gender/age/photo completeness scores
  4. booth_metrics      — voter-density signal for booths without pulse events
  5. ac_metrics         — rollup from booth_metrics
  6. booth_panchayat_mapping — inferred from section names
  7. Neo4j ontology     — applies all graph constraints

Run:
  python -m ingestion.ingest_all_features              # full pipeline
  python -m ingestion.ingest_all_features --dry-run    # stats only, no writes
  python -m ingestion.ingest_all_features --step demographics
  # steps: demographics | quality | booth_metrics | ac_metrics | panchayat | ontology
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ROOT     = Path(__file__).parents[1]
JSON_DIR = ROOT / "data" / "PoolBoothData_JSON"
AC_ID    = "GKP_322"
AC_NO    = 322

sys.path.insert(0, str(ROOT))

# ── Load & aggregate all voter records ───────────────────────────────────────

def load_booth_stats() -> dict[int, dict]:
    """Aggregate per-part (=booth) statistics from all JSON files.
    Returns mapping: part_no → stats dict.
    """
    files = sorted(JSON_DIR.glob("part_*.json"))
    booth_stats: dict[int, dict] = {}

    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        part = data["metadata"]["part_number"]
        voters = data.get("voter_records", [])

        gender_m = gender_f = gender_o = 0
        age_18_25 = age_26_40 = age_40_60 = age_60p = 0
        epic_ok = epic_missing = 0
        age_ok = age_missing = 0
        photo_ok = 0
        section_names: list[str] = []

        for v in voters:
            g = (v.get("gender") or "").lower()
            if g == "male":   gender_m += 1
            elif g == "female": gender_f += 1
            else:             gender_o += 1

            age = v.get("age")
            if age and str(age).isdigit():
                a = int(age)
                age_ok += 1
                if 18 <= a <= 25:   age_18_25 += 1
                elif 26 <= a <= 40: age_26_40 += 1
                elif 41 <= a <= 60: age_40_60 += 1
                elif a > 60:        age_60p += 1
            else:
                age_missing += 1

            vid = (v.get("voter_id") or "").strip()
            if vid and len(vid) >= 8: epic_ok += 1
            else:                      epic_missing += 1

            if v.get("photo_available"): photo_ok += 1

            sn = (v.get("section_name") or "").strip()
            if sn and sn not in section_names:
                section_names.append(sn)

        total = len(voters)
        booth_stats[part] = {
            "total":        total,
            "male":         gender_m,
            "female":       gender_f,
            "other":        gender_o,
            "age_18_25":    age_18_25,
            "age_26_40":    age_26_40,
            "age_40_60":    age_40_60,
            "age_60_plus":  age_60p,
            "epic_ok":      epic_ok,
            "epic_missing": epic_missing,
            "age_ok":       age_ok,
            "age_missing":  age_missing,
            "photo_ok":     photo_ok,
            "sections":     section_names,
            "top_section":  section_names[0] if section_names else "",
        }

    logger.info("Loaded stats for %d parts from %d JSON files", len(booth_stats), len(files))
    return booth_stats


# ── Step 1: booth_master — station names + locality hints ────────────────────

def infer_locality(section_names: list[str]) -> str:
    """Extract a clean locality label from OCR'd section names."""
    if not section_names:
        return ""
    # Use the most common prefix word as the locality hint
    words = section_names[0].split()
    # Skip generic Hindi/OCR artefacts
    skip = {"no.", "no,", "jn.", "#", "-", "of", "at", "tola"}
    label = " ".join(w for w in words[:4] if w.lower() not in skip)
    return label[:60]


def infer_station_name(section_names: list[str], part: int) -> str:
    """Build a polling station name from section data."""
    if not section_names:
        return f"Polling Booth {part}"
    # Most sections are named for the hamlet/ward — use the first two
    names = section_names[:2]
    if len(names) == 1:
        return names[0][:120]
    # If they share a common prefix, collapse
    words0 = names[0].split()
    words1 = names[1].split()
    shared = []
    for a, b in zip(words0, words1):
        if a.lower() == b.lower():
            shared.append(a)
        else:
            break
    if shared and len(shared) >= 2:
        return " ".join(shared)[:120]
    return names[0][:120]


def step_booth_master(stats: dict[int, dict], engine, dry_run=False) -> int:
    from sqlalchemy import text
    updated = 0
    rows = []
    for part, s in stats.items():
        booth_id     = f"GKP_{AC_NO}_{part:03d}"
        station_name = infer_station_name(s["sections"], part)
        locality     = infer_locality(s["sections"])
        # Top section as panchayat hint
        panchayat    = (s["sections"][0][:80]) if s["sections"] else ""
        rows.append({
            "booth_id": booth_id,
            "station":  station_name,
            "locality": locality,
            "panchayat_hint": panchayat,
        })

    if not dry_run:
        with engine.begin() as conn:
            for r in rows:
                conn.execute(text("""
                    UPDATE booth_master
                       SET polling_station_name = COALESCE(NULLIF(polling_station_name,''), :station),
                           locality_hint        = COALESCE(NULLIF(locality_hint,''), :locality),
                           panchayat_hint       = COALESCE(NULLIF(panchayat_hint,''), :panchayat_hint),
                           updated_at           = NOW()
                     WHERE booth_id = :booth_id
                """), r)
                updated += 1
    else:
        updated = len(rows)

    logger.info("Step booth_master: %d booths %s", updated, "would update" if dry_run else "updated")
    return updated


# ── Step 2: ac_demographics ───────────────────────────────────────────────────

def step_demographics(stats: dict[int, dict], engine, dry_run=False) -> None:
    from sqlalchemy import text
    total = sum(s["total"]      for s in stats.values())
    male  = sum(s["male"]       for s in stats.values())
    fem   = sum(s["female"]     for s in stats.values())
    other = sum(s["other"]      for s in stats.values())
    a1825 = sum(s["age_18_25"]  for s in stats.values())
    a2640 = sum(s["age_26_40"]  for s in stats.values())
    a4060 = sum(s["age_40_60"]  for s in stats.values())
    a60p  = sum(s["age_60_plus"] for s in stats.values())

    logger.info("Demographics — Total:%d M:%d F:%d O:%d | 18-25:%d 26-40:%d 40-60:%d 60+:%d",
                total, male, fem, other, a1825, a2640, a4060, a60p)

    if not dry_run:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO ac_demographics
                    (ac_id, total_voters, male_voters, female_voters, other_voters,
                     age_18_25, age_26_40, age_40_60, age_60_plus,
                     data_source, last_updated, notes)
                VALUES
                    (:ac_id, :total, :male, :female, :other,
                     :a1825, :a2640, :a4060, :a60p,
                     'PoolBoothData_JSON_2026', NOW(),
                     'Aggregated from 177-part 2026 SIR electoral roll (AC 322 Gorakhpur City)')
                ON CONFLICT (ac_id) DO UPDATE
                    SET total_voters  = EXCLUDED.total_voters,
                        male_voters   = EXCLUDED.male_voters,
                        female_voters = EXCLUDED.female_voters,
                        other_voters  = EXCLUDED.other_voters,
                        age_18_25     = EXCLUDED.age_18_25,
                        age_26_40     = EXCLUDED.age_26_40,
                        age_40_60     = EXCLUDED.age_40_60,
                        age_60_plus   = EXCLUDED.age_60_plus,
                        data_source   = EXCLUDED.data_source,
                        last_updated  = NOW(),
                        notes         = EXCLUDED.notes
            """), {
                "ac_id": AC_ID, "total": total, "male": male, "female": fem, "other": other,
                "a1825": a1825, "a2640": a2640, "a4060": a4060, "a60p": a60p,
            })
        logger.info("ac_demographics upserted for %s", AC_ID)


# ── Step 3: data_quality_metrics ─────────────────────────────────────────────

def quality_score(epic_ok: int, epic_miss: int, age_ok: int, age_miss: int,
                  photo_ok: int, total: int) -> tuple[float, str, list[str]]:
    """Compute a 0–1 overall quality score and label from field completeness."""
    if total == 0:
        return 0.0, "UNKNOWN", ["no_voters"]

    epic_rate  = epic_ok  / total
    age_rate   = age_ok   / total
    photo_rate = photo_ok / total

    score = epic_rate * 0.45 + age_rate * 0.35 + photo_rate * 0.20
    score = round(min(score, 1.0), 4)

    reasons = []
    if epic_rate < 0.8:  reasons.append("low_epic_coverage")
    if age_rate  < 0.9:  reasons.append("missing_age_data")
    if photo_rate < 0.5: reasons.append("photos_not_digitised")

    if score >= 0.85:   label = "HIGH"
    elif score >= 0.65: label = "MEDIUM"
    else:               label = "LOW"

    return score, label, reasons


def step_data_quality(stats: dict[int, dict], engine, dry_run=False) -> int:
    from sqlalchemy import text
    now = datetime.now(timezone.utc)
    rows = []

    for part, s in sorted(stats.items()):
        booth_id = f"GKP_{AC_NO}_{part:03d}"
        score, label, reasons = quality_score(
            s["epic_ok"], s["epic_missing"],
            s["age_ok"],  s["age_missing"],
            s["photo_ok"], s["total"],
        )
        total = s["total"]
        epic_ok, age_ok, photo_ok = s["epic_ok"], s["age_ok"], s["photo_ok"]

        # Infer source breakdown (we only have electoral-roll data)
        rows.append({
            "id":                   str(uuid.uuid4()),
            "booth_id":             booth_id,
            "computed_at":          now,
            "window_days":          365,
            "total_events":         total,
            "unique_sources":       1,
            "youtube_pct":          0.0,
            "news_pct":             0.0,
            "survey_pct":           0.0,
            "field_note_pct":       0.0,
            "booth_mapped_pct":     1.0,
            "ac_mapped_pct":        0.0,
            "avg_geo_confidence":   1.0,
            "avg_nlp_confidence":   round(epic_ok / max(total, 1), 4),
            "llm_extracted_pct":    0.0,
            "entity_match_rate":    round(epic_ok / max(total, 1), 4),
            "missing_entity_pct":   round(s["epic_missing"] / max(total, 1), 4),
            "source_diversity_score": 0.1,
            "overall_quality_score": score,
            "quality_label":        label,
            "quality_reasons":      json.dumps(reasons),
        })

    if not dry_run:
        insert_sql = text("""
            INSERT INTO data_quality_metrics
                (id, booth_id, computed_at, window_days,
                 total_events, unique_sources,
                 youtube_pct, news_pct, survey_pct, field_note_pct,
                 booth_mapped_pct, ac_mapped_pct,
                 avg_geo_confidence, avg_nlp_confidence,
                 llm_extracted_pct, entity_match_rate, missing_entity_pct,
                 source_diversity_score, overall_quality_score,
                 quality_label, quality_reasons)
            VALUES
                (:id, :booth_id, :computed_at, :window_days,
                 :total_events, :unique_sources,
                 :youtube_pct, :news_pct, :survey_pct, :field_note_pct,
                 :booth_mapped_pct, :ac_mapped_pct,
                 :avg_geo_confidence, :avg_nlp_confidence,
                 :llm_extracted_pct, :entity_match_rate, :missing_entity_pct,
                 :source_diversity_score, :overall_quality_score,
                 :quality_label, :quality_reasons)
            ON CONFLICT DO NOTHING
        """)
        with engine.begin() as conn:
            for r in rows:
                conn.execute(insert_sql, r)

    logger.info("Step data_quality_metrics: %d booth rows %s",
                len(rows), "would insert" if dry_run else "inserted")
    return len(rows)


# ── Step 4: booth_metrics — voter-density signal for uncovered booths ─────────

def step_booth_metrics(stats: dict[int, dict], engine, dry_run=False) -> int:
    """Seed booth_metrics for booths that have no pulse-event coverage yet.
    Uses voter-count ratios to estimate a neutral BJp/Opp signal,
    and marks data_confidence from the quality score.
    """
    from sqlalchemy import text

    # Fetch booths already in booth_metrics
    with engine.connect() as conn:
        covered = {r[0] for r in conn.execute(sa.text("SELECT DISTINCT booth_id FROM booth_metrics")).fetchall()}

    now = datetime.now(timezone.utc)
    rows = []
    total_voters_ac = sum(s["total"] for s in stats.values())
    max_voters = max((s["total"] for s in stats.values()), default=1)

    for part, s in sorted(stats.items()):
        booth_id = f"GKP_{AC_NO}_{part:03d}"
        if booth_id in covered:
            continue  # already has real signal, don't overwrite

        total = s["total"]
        score, label, reasons = quality_score(
            s["epic_ok"], s["epic_missing"],
            s["age_ok"], s["age_missing"],
            s["photo_ok"], total,
        )
        # Neutral signal — no ground truth yet
        bjp_pulse   = 0.0
        opp_pulse   = 0.0
        digital_lean = 0.0
        event_count = total  # treat each voter record as a census event

        rows.append({
            "booth_id":              booth_id,
            "window_start":          now,
            "window_end":            now,
            "bjp_pulse_score":       bjp_pulse,
            "opp_pulse_score":       opp_pulse,
            "digital_lean":          digital_lean,
            "digital_lean_label":    "NEUTRAL",
            "top_issue":             "electoral_roll_coverage",
            "issue_breakdown":       json.dumps({"electoral_roll_coverage": total}),
            "issue_momentum":        json.dumps({}),
            "scheme_gap_issues":     json.dumps([]),
            "event_count":           event_count,
            "data_confidence":       score,
            "confidence_label":      label,
            "last_computed_at":      now,
            "signal_consistency_score": score,
            "has_contradiction":     False,
            "dominant_narrative":    "Voter roll data loaded",
            "narrative_strength":    score,
            "quality_score":         score,
        })

    if not dry_run and rows:
        insert_sql = text("""
            INSERT INTO booth_metrics
                (booth_id, window_start, window_end,
                 bjp_pulse_score, opp_pulse_score, digital_lean, digital_lean_label,
                 top_issue, issue_breakdown, issue_momentum, scheme_gap_issues,
                 event_count, data_confidence, confidence_label, last_computed_at,
                 signal_consistency_score, has_contradiction,
                 dominant_narrative, narrative_strength, quality_score)
            VALUES
                (:booth_id, :window_start, :window_end,
                 :bjp_pulse_score, :opp_pulse_score, :digital_lean, :digital_lean_label,
                 :top_issue, :issue_breakdown, :issue_momentum, :scheme_gap_issues,
                 :event_count, :data_confidence, :confidence_label, :last_computed_at,
                 :signal_consistency_score, :has_contradiction,
                 :dominant_narrative, :narrative_strength, :quality_score)
            ON CONFLICT DO NOTHING
        """)
        with engine.begin() as conn:
            for r in rows:
                conn.execute(insert_sql, r)

    logger.info("Step booth_metrics: %d new rows %s (already covered: %d)",
                len(rows), "would insert" if dry_run else "inserted", len(covered))
    return len(rows)


# ── Step 5: ac_metrics rollup ────────────────────────────────────────────────

def step_ac_metrics(engine, dry_run=False) -> None:
    from sqlalchemy import text

    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT
                AVG(bjp_pulse_score)  AS bjp,
                AVG(opp_pulse_score)  AS opp,
                AVG(digital_lean)     AS lean,
                COUNT(DISTINCT booth_id) AS coverage,
                SUM(event_count)      AS events,
                (SELECT COUNT(*) FROM booth_master WHERE ac_id = :ac_id) AS total_booths,
                (SELECT jsonb_object_agg(top_issue, cnt)
                 FROM (
                     SELECT top_issue, COUNT(*) AS cnt
                     FROM booth_metrics
                     WHERE top_issue IS NOT NULL
                     GROUP BY top_issue ORDER BY cnt DESC LIMIT 5
                 ) t) AS top_issues
            FROM (
                SELECT DISTINCT ON (booth_id) booth_id,
                       bjp_pulse_score, opp_pulse_score, digital_lean,
                       event_count, top_issue
                FROM booth_metrics
                ORDER BY booth_id, window_start DESC
            ) latest
        """), {"ac_id": AC_ID}).mappings().fetchone()

    logger.info("AC rollup — BJp:%.3f Opp:%.3f Lean:%.3f Coverage:%d/%d Events:%d",
                row["bjp"] or 0, row["opp"] or 0, row["lean"] or 0,
                row["coverage"] or 0, row["total_booths"] or 0, row["events"] or 0)

    if not dry_run:
        now = datetime.now(timezone.utc)
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO ac_metrics
                    (ac_id, window_start, bjp_pulse_score, opp_pulse_score,
                     digital_lean, top_issues, booth_coverage, total_booths,
                     event_count, last_computed_at)
                VALUES
                    (:ac_id, :now, :bjp, :opp, :lean, :issues,
                     :coverage, :total, :events, :now)
                ON CONFLICT (ac_id, window_start) DO UPDATE
                    SET bjp_pulse_score = EXCLUDED.bjp_pulse_score,
                        opp_pulse_score = EXCLUDED.opp_pulse_score,
                        digital_lean    = EXCLUDED.digital_lean,
                        top_issues      = EXCLUDED.top_issues,
                        booth_coverage  = EXCLUDED.booth_coverage,
                        total_booths    = EXCLUDED.total_booths,
                        event_count     = EXCLUDED.event_count,
                        last_computed_at = EXCLUDED.last_computed_at
            """), {
                "ac_id": AC_ID, "now": now,
                "bjp":  float(row["bjp"] or 0),
                "opp":  float(row["opp"] or 0),
                "lean": float(row["lean"] or 0),
                "issues":    json.dumps(dict(row["top_issues"] or {})),
                "coverage":  row["coverage"] or 0,
                "total":     row["total_booths"] or 0,
                "events":    row["events"] or 0,
            })
        logger.info("ac_metrics upserted for %s", AC_ID)


# ── Step 6: booth_panchayat_mapping ──────────────────────────────────────────

def step_panchayat_mapping(stats: dict[int, dict], engine, dry_run=False) -> int:
    """Infer booth→panchayat mapping from section name common prefixes."""
    from sqlalchemy import text

    # Group parts by inferred locality prefix
    locality_parts: dict[str, list[int]] = defaultdict(list)
    for part, s in sorted(stats.items()):
        locality = infer_locality(s["sections"])
        prefix = " ".join(locality.split()[:2]) if locality else f"Zone_{(part-1)//10 + 1}"
        locality_parts[prefix].append(part)

    # Build a synthetic panchayat per locality cluster
    panchayat_rows: list[dict] = []
    mapping_rows:   list[dict] = []

    for idx, (locality, parts) in enumerate(sorted(locality_parts.items()), 1):
        pan_id   = f"PAN_{AC_NO}_{idx:03d}"
        pan_name = locality or f"Panchayat {idx}"
        panchayat_rows.append({"id": pan_id, "name": pan_name, "ac_id": AC_ID})
        for part in parts:
            booth_id = f"GKP_{AC_NO}_{part:03d}"
            mapping_rows.append({"booth_id": booth_id, "panchayat_id": pan_id})

    logger.info("Step panchayat_mapping: %d panchayats, %d booth mappings",
                len(panchayat_rows), len(mapping_rows))

    if not dry_run:
        with engine.begin() as conn:
            for r in panchayat_rows:
                conn.execute(text("""
                    INSERT INTO panchayat_master (panchayat_id, gp_name, block_name, district_id)
                    VALUES (:id, :name, :block, :district_id)
                    ON CONFLICT (panchayat_id) DO NOTHING
                """), {"id": r["id"], "name": r["name"], "block": "Gorakhpur Urban", "district_id": "DIST_148"})

            for r in mapping_rows:
                conn.execute(text("""
                    INSERT INTO booth_panchayat_mapping (booth_id, panchayat_id, match_method)
                    VALUES (:booth_id, :panchayat_id, 'section_name_cluster')
                    ON CONFLICT DO NOTHING
                """), r)

    return len(mapping_rows)


# ── Step 7: Neo4j ontology constraints ───────────────────────────────────────

def step_neo4j_ontology(dry_run=False) -> dict:
    from backend.db import get_neo4j_session

    CONSTRAINTS = [
        # Core hierarchy
        "CREATE CONSTRAINT IF NOT EXISTS FOR (s:State)              REQUIRE s.state_id   IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (d:District)           REQUIRE d.district_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (ac:AssemblyConstituency) REQUIRE ac.ac_id   IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (b:Booth)              REQUIRE b.booth_id    IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (b:Booth)              REQUIRE b.id          IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (sec:Section)          REQUIRE sec.id        IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (h:Household)          REQUIRE h.id          IS UNIQUE",
        # Voter & person
        "CREATE CONSTRAINT IF NOT EXISTS FOR (v:Voter)              REQUIRE v.voter_key   IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person)             REQUIRE p.id          IS UNIQUE",
        # Political actors
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Candidate)          REQUIRE c.candidate_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (pa:Party)             REQUIRE pa.party_id   IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (pa:Party)             REQUIRE pa.name       IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Issue)              REQUIRE i.code        IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Event)              REQUIRE e.event_id    IS UNIQUE",
        # Indexes
        "CREATE INDEX IF NOT EXISTS FOR (v:Voter) ON (v.epic_id)",
        "CREATE INDEX IF NOT EXISTS FOR (v:Voter) ON (v.booth_id)",
        "CREATE INDEX IF NOT EXISTS FOR (v:Voter) ON (v.name_norm)",
        "CREATE INDEX IF NOT EXISTS FOR (b:Booth) ON (b.ac_id)",
    ]

    stats = {}
    if not dry_run:
        with get_neo4j_session() as session:
            applied = 0
            for stmt in CONSTRAINTS:
                try:
                    session.run(stmt)
                    applied += 1
                except Exception as e:
                    logger.warning("Constraint skipped (%s): %s", type(e).__name__, stmt[:60])

            # Count nodes
            for label in ["Voter", "Household", "Section", "Booth",
                          "AssemblyConstituency", "Person", "Candidate"]:
                cnt = session.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()["c"]
                stats[label] = cnt
                logger.info("  Neo4j %-25s %d", label, cnt)

            applied_constraints = session.run(
                "SHOW CONSTRAINTS YIELD name RETURN count(*) AS c"
            ).single()["c"]
            stats["constraints_applied"] = applied_constraints

    logger.info("Neo4j ontology step complete: %s", stats)
    return stats


# ── Print final summary ───────────────────────────────────────────────────────

def print_summary(engine, neo4j_stats: dict) -> None:
    from sqlalchemy import text
    print("\n" + "="*62)
    print("  INGESTION SUMMARY")
    print("="*62)
    with engine.connect() as conn:
        for t in ["booth_master", "ac_demographics", "data_quality_metrics",
                  "booth_metrics", "ac_metrics", "booth_panchayat_mapping"]:
            cnt = conn.execute(sa.text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
            print(f"  {t:<32} {cnt:>8,} rows")

    if neo4j_stats:
        print()
        for k, v in neo4j_stats.items():
            print(f"  Neo4j {k:<26} {v:>8,}")
    print("="*62 + "\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

import sqlalchemy as sa  # noqa: E402 (after sys.path setup)

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest all features from PoolBoothData_JSON")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--step", choices=["booth", "demographics", "quality",
                                           "booth_metrics", "ac_metrics",
                                           "panchayat", "ontology"])
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    engine = sa.create_engine(__import__("os").environ["POSTGRES_URL"])

    logger.info("Loading booth statistics from JSON…")
    stats = load_booth_stats()

    run_all = args.step is None
    neo4j_stats: dict = {}

    if run_all or args.step == "booth":
        step_booth_master(stats, engine, dry_run=args.dry_run)

    if run_all or args.step == "demographics":
        step_demographics(stats, engine, dry_run=args.dry_run)

    if run_all or args.step == "quality":
        step_data_quality(stats, engine, dry_run=args.dry_run)

    if run_all or args.step == "booth_metrics":
        step_booth_metrics(stats, engine, dry_run=args.dry_run)

    if run_all or args.step == "ac_metrics":
        step_ac_metrics(engine, dry_run=args.dry_run)

    if run_all or args.step == "panchayat":
        step_panchayat_mapping(stats, engine, dry_run=args.dry_run)

    if run_all or args.step == "ontology":
        neo4j_stats = step_neo4j_ontology(dry_run=args.dry_run)

    if not args.dry_run:
        print_summary(engine, neo4j_stats)
    else:
        logger.info("Dry-run complete — no DB changes made.")


if __name__ == "__main__":
    main()
