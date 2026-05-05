"""All database queries for the FastAPI layer."""
from __future__ import annotations
import functools
from sqlalchemy import text
from .db import get_neo4j_session, get_pg_engine


# ── Booth list for AC ─────────────────────────────────────────────────────────
@functools.lru_cache(maxsize=32)
def get_booths_for_ac(ac_id: str) -> list[dict]:
    with get_pg_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT
                b.booth_id, b.booth_number, b.polling_station_name AS name,
                b.locality_hint, b.total_voters, b.male_voters, b.female_voters,
                bm.bjp_pulse_score, bm.opp_pulse_score, bm.digital_lean,
                bm.digital_lean_label, bm.top_issue,
                bm.confidence_label, bm.event_count
            FROM booth_master b
            LEFT JOIN LATERAL (
                SELECT * FROM booth_metrics
                WHERE booth_id = b.booth_id
                ORDER BY window_start DESC LIMIT 1
            ) bm ON TRUE
            WHERE b.ac_id = :ac_id
            ORDER BY b.booth_number
        """), {"ac_id": ac_id}).mappings().fetchall()
    return [dict(r) for r in rows]


# ── Single booth summary ──────────────────────────────────────────────────────
def get_booth_summary(booth_id: str) -> dict | None:
    with get_pg_engine().connect() as conn:
        row = conn.execute(text("""
            SELECT b.*, bm.bjp_pulse_score, bm.opp_pulse_score,
                   bm.digital_lean, bm.digital_lean_label,
                   bm.top_issue, bm.issue_breakdown, bm.issue_momentum,
                   bm.confidence_label, bm.event_count, bm.data_confidence
            FROM booth_master b
            LEFT JOIN LATERAL (
                SELECT * FROM booth_metrics WHERE booth_id = b.booth_id
                ORDER BY window_start DESC LIMIT 1
            ) bm ON TRUE
            WHERE b.booth_id = :bid
        """), {"bid": booth_id}).mappings().fetchone()
    return dict(row) if row else None


# ── Historical results ────────────────────────────────────────────────────────
def get_booth_history(booth_id: str) -> list[dict]:
    with get_pg_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT election_year, party, votes, vote_share, winner_flag
            FROM booth_results WHERE booth_id = :bid
            ORDER BY election_year ASC, vote_share DESC
        """), {"bid": booth_id}).mappings().fetchall()
    return [dict(r) for r in rows]


# ── Top issues ────────────────────────────────────────────────────────────────
def get_booth_issues(booth_id: str, limit: int = 5, days: int = 30) -> list[dict]:
    with get_pg_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT final_issue AS issue,
                   COUNT(*) AS mention_count,
                   ROUND(AVG(final_polarity)::numeric, 2) AS avg_polarity,
                   SUM(CASE WHEN final_polarity = -1 THEN 1 ELSE 0 END) AS negative_count,
                   SUM(CASE WHEN final_polarity =  1 THEN 1 ELSE 0 END) AS positive_count
            FROM pulse_events
            WHERE mapped_booth_id = :bid
              AND final_issue IS NOT NULL
              AND created_at >= NOW() - INTERVAL ':days days'
            GROUP BY final_issue
            ORDER BY mention_count DESC
            LIMIT :limit
        """), {"bid": booth_id, "limit": limit, "days": days}).mappings().fetchall()
    return [dict(r) for r in rows]


# ── Pulse time-series ─────────────────────────────────────────────────────────
def get_booth_pulse(booth_id: str, days: int = 7) -> list[dict]:
    with get_pg_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT entity,
                   ROUND((SUM(final_polarity * final_confidence * CASE source_type
                       WHEN 'survey' THEN 1.0 WHEN 'youtube' THEN 0.6
                       WHEN 'news' THEN 0.4 ELSE 0.5 END) /
                       NULLIF(SUM(final_confidence * CASE source_type
                       WHEN 'survey' THEN 1.0 WHEN 'youtube' THEN 0.6
                       WHEN 'news' THEN 0.4 ELSE 0.5 END), 0))::numeric, 3) AS pulse_score,
                   COUNT(*) AS event_count
            FROM pulse_events
            WHERE mapped_booth_id = :bid
              AND entity IN ('BJP','SP','BSP','Congress','Akhilesh Yadav',
                             'Yogi Adityanath','Mayawati','Narendra Modi')
              AND created_at >= NOW() - (:days || ' days')::interval
            GROUP BY entity
            ORDER BY pulse_score DESC
        """), {"bid": booth_id, "days": days}).mappings().fetchall()
    return [dict(r) for r in rows]


# ── Backing comments ──────────────────────────────────────────────────────────
def get_booth_comments(booth_id: str, limit: int = 10, source: str | None = None) -> list[dict]:
    source_filter = "AND source_type = :source" if source and source != "all" else ""
    with get_pg_engine().connect() as conn:
        rows = conn.execute(text(f"""
            SELECT id::text, text_raw, entity, final_polarity AS polarity,
                   final_issue AS issue, final_confidence AS confidence,
                   source_type AS source, created_at::text
            FROM pulse_events
            WHERE mapped_booth_id = :bid
              AND final_confidence >= 0.55
              {source_filter}
            ORDER BY created_at DESC
            LIMIT :limit
        """), {"bid": booth_id, "limit": limit, "source": source}).mappings().fetchall()
    return [dict(r) for r in rows]


# ── Candidates ────────────────────────────────────────────────────────────────
def get_ac_candidates(ac_id: str) -> list[dict]:
    with get_pg_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT cm.candidate_id, cm.name, cm.party,
                   cm.is_incumbent, cm.is_primary_opp,
                   ca.criminal_cases, ca.serious_cases,
                   ca.total_assets, ca.total_liabilities,
                   ca.education, ca.age,
                   -- Candidate-level sentiment (last 30 days)
                   ROUND(AVG(pe.final_polarity * pe.final_confidence)::numeric, 3)
                       AS sentiment_score,
                   COUNT(pe.id) AS mention_count
            FROM candidate_master cm
            LEFT JOIN candidate_affidavits ca USING (candidate_id)
            LEFT JOIN pulse_events pe
                ON pe.entity ILIKE '%' || cm.name || '%'
               OR pe.entity = cm.party
            WHERE cm.ac_id = :ac_id
            GROUP BY cm.candidate_id, cm.name, cm.party, cm.is_incumbent,
                     cm.is_primary_opp, ca.criminal_cases, ca.serious_cases,
                     ca.total_assets, ca.total_liabilities, ca.education, ca.age
            ORDER BY cm.is_incumbent DESC, cm.party
        """), {"ac_id": ac_id}).mappings().fetchall()
    return [dict(r) for r in rows]


# ── Candidate issue sentiment breakdown ───────────────────────────────────────
def get_candidate_issue_sentiment(candidate_name: str, party: str, booth_id: str) -> list[dict]:
    with get_pg_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT final_issue AS issue,
                   ROUND(AVG(final_polarity * final_confidence)::numeric, 3) AS score,
                   COUNT(*) AS mentions,
                   SUM(CASE WHEN final_polarity=1 THEN 1 ELSE 0 END) AS positive,
                   SUM(CASE WHEN final_polarity=-1 THEN 1 ELSE 0 END) AS negative
            FROM pulse_events
            WHERE (entity ILIKE '%' || :name || '%' OR entity = :party)
              AND mapped_booth_id = :bid
              AND final_issue IS NOT NULL
              AND created_at >= NOW() - INTERVAL '30 days'
            GROUP BY final_issue
            ORDER BY mentions DESC
        """), {"name": candidate_name, "party": party, "bid": booth_id}).mappings().fetchall()
    return [dict(r) for r in rows]


# ── Scheme gap ────────────────────────────────────────────────────────────────
def get_scheme_gap(booth_id: str) -> list[dict]:
    """Returns rich scheme gap rows from the pre-computed scheme_gap_analysis table."""
    with get_pg_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT scheme_name, issue_tag, completion_status,
                   beneficiary_count, gap_type, gap_label, priority,
                   positive_events, negative_events, total_events, avg_sentiment,
                   computed_at
            FROM scheme_gap_analysis
            WHERE booth_id = :bid
            ORDER BY computed_at DESC,
                     CASE priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END
        """), {"bid": booth_id}).mappings().fetchall()
    return [dict(r) for r in rows]


# ── Data quality ──────────────────────────────────────────────────────────────
def get_booth_quality(booth_id: str) -> dict | None:
    """Most recent quality metrics row for the booth."""
    with get_pg_engine().connect() as conn:
        row = conn.execute(text("""
            SELECT booth_id, computed_at, window_days, total_events, unique_sources,
                   youtube_pct, news_pct, survey_pct, field_note_pct,
                   booth_mapped_pct, ac_mapped_pct,
                   avg_geo_confidence, avg_nlp_confidence,
                   llm_extracted_pct, entity_match_rate, missing_entity_pct,
                   source_diversity_score, overall_quality_score,
                   quality_label, quality_reasons
            FROM data_quality_metrics
            WHERE booth_id = :bid
            ORDER BY computed_at DESC
            LIMIT 1
        """), {"bid": booth_id}).mappings().fetchone()
    if not row:
        return None
    result = dict(row)
    import json
    if isinstance(result.get("quality_reasons"), str):
        result["quality_reasons"] = json.loads(result["quality_reasons"])
    return result


# ── Narratives ────────────────────────────────────────────────────────────────
def get_booth_narratives(booth_id: str, limit: int = 5) -> list[dict]:
    """Most recent narrative detections for the booth, sorted by strength."""
    with get_pg_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT narrative_type, strength, description,
                   top_issues, top_entities, evidence_count, confidence, computed_at
            FROM booth_narratives
            WHERE booth_id = :bid
            ORDER BY computed_at DESC, strength DESC
            LIMIT :limit
        """), {"bid": booth_id, "limit": limit}).mappings().fetchall()
    import json
    result = []
    for r in rows:
        row = dict(r)
        for field in ("top_issues", "top_entities"):
            if isinstance(row.get(field), str):
                row[field] = json.loads(row[field])
        result.append(row)
    return result


# ── Contradictions ────────────────────────────────────────────────────────────
def get_booth_contradictions(booth_id: str) -> list[dict]:
    """Contradiction flags for the booth from the most recent compute window."""
    with get_pg_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT entity, issue, source_a, source_b,
                   polarity_a, polarity_b, delta,
                   events_a, events_b, consistency_score, flag_label, computed_at
            FROM contradiction_flags
            WHERE booth_id = :bid
            ORDER BY computed_at DESC, delta DESC
        """), {"bid": booth_id}).mappings().fetchall()
    return [dict(r) for r in rows]
