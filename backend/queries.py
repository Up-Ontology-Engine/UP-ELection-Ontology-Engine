"""All database queries for the FastAPI layer."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text

from .cache import cached
from .db import get_neo4j_session, get_pg_engine

# Logical → physical AC-ID aliases (frontend uses logical, DBs use physical)
_PG_AC_ALIASES: dict[str, str] = {
    "GKP_URBAN": "GKP_322",
    "GKP_RURAL": "GKP_323",
}


def _rac(ac_id: str) -> str:
    """Resolve a logical AC-ID to its physical DB counterpart."""
    return _PG_AC_ALIASES.get(ac_id, ac_id)


# ── Booth geo data (lat/lon + pulse scores) ───────────────────────────────────
def get_booth_geo(ac_id: str) -> list[dict]:
    """Return booth lat/lon + latest pulse metrics for all geocoded booths in an AC."""
    resolved = _rac(ac_id)
    with get_pg_engine().connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT
                b.booth_id, b.booth_number, b.polling_station_name AS name,
                b.locality_hint, b.total_voters, b.lat, b.lon,
                bm.bjp_pulse_score, bm.opp_pulse_score,
                bm.digital_lean, bm.digital_lean_label,
                bm.top_issue, bm.confidence_label
            FROM booth_master b
            LEFT JOIN LATERAL (
                SELECT * FROM booth_metrics
                WHERE booth_id = b.booth_id
                ORDER BY window_start DESC LIMIT 1
            ) bm ON TRUE
            WHERE b.ac_id = :ac_id
              AND b.lat IS NOT NULL
              AND b.booth_id NOT LIKE '%_TOTAL'
            ORDER BY b.booth_number
        """),
                {"ac_id": resolved},
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


# ── Booth list for AC ─────────────────────────────────────────────────────────
@cached("cache:booth_list:{ac_id}", ttl=60)
def get_booths_for_ac(ac_id: str) -> list[dict]:
    resolved = _rac(ac_id)
    with get_pg_engine().connect() as conn:
        rows = (
            conn.execute(
                text("""
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
        """),
                {"ac_id": resolved},
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


# ── Single booth summary ──────────────────────────────────────────────────────
def get_booth_summary(booth_id: str) -> dict | None:
    with get_pg_engine().connect() as conn:
        row = (
            conn.execute(
                text("""
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
        """),
                {"bid": booth_id},
            )
            .mappings()
            .fetchone()
        )
    return dict(row) if row else None


# ── Historical results ────────────────────────────────────────────────────────
def get_booth_history(booth_id: str) -> list[dict]:
    with get_pg_engine().connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT election_year, party, votes, vote_share, winner_flag
            FROM booth_results WHERE booth_id = :bid
            ORDER BY election_year ASC, vote_share DESC
        """),
                {"bid": booth_id},
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


# ── Top issues ────────────────────────────────────────────────────────────────
def get_booth_issues(booth_id: str, limit: int = 12, days: int = 365) -> list[dict]:
    with get_pg_engine().connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT final_issue AS issue,
                   COUNT(*) AS mention_count,
                   ROUND(AVG(final_polarity)::numeric, 2) AS avg_polarity,
                   SUM(CASE WHEN final_polarity = -1 THEN 1 ELSE 0 END) AS negative_count,
                   SUM(CASE WHEN final_polarity =  1 THEN 1 ELSE 0 END) AS positive_count
            FROM pulse_events
            WHERE (
                mapped_booth_id = :bid
                OR (mapped_booth_id IS NULL AND mapped_ac_id = (
                    SELECT ac_id FROM booth_master WHERE booth_id = :bid
                ))
            )
              AND final_issue IS NOT NULL
            GROUP BY final_issue
            ORDER BY mention_count DESC
            LIMIT :limit
        """),
                {"bid": booth_id, "limit": limit},
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


# ── Pulse by entity ───────────────────────────────────────────────────────────
def get_booth_pulse(booth_id: str, days: int = 365) -> list[dict]:
    with get_pg_engine().connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT entity,
                   ROUND((SUM(final_polarity * final_confidence * CASE source_type
                       WHEN 'survey' THEN 1.0 WHEN 'youtube' THEN 0.6
                       WHEN 'news' THEN 0.4 ELSE 0.5 END) /
                       NULLIF(SUM(final_confidence * CASE source_type
                       WHEN 'survey' THEN 1.0 WHEN 'youtube' THEN 0.6
                       WHEN 'news' THEN 0.4 ELSE 0.5 END), 0))::numeric, 3) AS pulse_score,
                   COUNT(*) AS event_count
            FROM pulse_events
            WHERE (
                mapped_booth_id = :bid
                OR (mapped_booth_id IS NULL AND mapped_ac_id = (
                    SELECT ac_id FROM booth_master WHERE booth_id = :bid
                ))
            )
              AND entity IS NOT NULL
            GROUP BY entity
            ORDER BY event_count DESC
        """),
                {"bid": booth_id},
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


# ── Pulse by source ───────────────────────────────────────────────────────────
def get_booth_source_breakdown(booth_id: str) -> list[dict]:
    with get_pg_engine().connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT source_type,
                   COUNT(*) AS event_count,
                   ROUND(AVG(final_polarity * final_confidence)::numeric, 3) AS avg_pulse,
                   SUM(CASE WHEN final_polarity =  1 THEN 1 ELSE 0 END) AS positive,
                   SUM(CASE WHEN final_polarity = -1 THEN 1 ELSE 0 END) AS negative,
                   SUM(CASE WHEN final_polarity =  0 THEN 1 ELSE 0 END) AS neutral
            FROM pulse_events
            WHERE (
                mapped_booth_id = :bid
                OR (mapped_booth_id IS NULL AND mapped_ac_id = (
                    SELECT ac_id FROM booth_master WHERE booth_id = :bid
                ))
            )
            GROUP BY source_type
            ORDER BY event_count DESC
        """),
                {"bid": booth_id},
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


# ── Backing comments ──────────────────────────────────────────────────────────
def get_booth_comments(booth_id: str, limit: int = 10, source: str | None = None) -> list[dict]:
    source_filter = "AND source_type = :source" if source and source != "all" else ""
    with get_pg_engine().connect() as conn:
        rows = (
            conn.execute(
                text(f"""
            SELECT id::text, text_raw, entity, final_polarity AS polarity,
                   final_issue AS issue, final_confidence AS confidence,
                   source_type AS source, created_at::text
            FROM pulse_events
            WHERE (
                mapped_booth_id = :bid
                OR (mapped_booth_id IS NULL AND mapped_ac_id = (
                    SELECT ac_id FROM booth_master WHERE booth_id = :bid
                ))
            )
              AND final_confidence >= 0.55
              {source_filter}
            ORDER BY final_confidence DESC, created_at DESC
            LIMIT :limit
        """),
                {"bid": booth_id, "limit": limit, "source": source},
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


# ── Candidates ────────────────────────────────────────────────────────────────
def get_ac_candidates(ac_id: str) -> list[dict]:
    """
    Returns enriched candidate list for an AC, joining across:
      candidate_master        — identity, profession, net_worth_rs   (007)
      candidate_affidavits    — assets, criminal cases, detail fields (007)
      candidate_party_history — vote totals, rank, result facts       (007)
      candidate_expense_detail — campaign spend, if available         (007)
      pulse_events            — live sentiment score + mention count

    Result rows are ordered by election rank (winner first), then party.
    """
    with get_pg_engine().connect() as conn:
        rows = (
            conn.execute(
                text("""
            WITH sentiment_cte AS (
                SELECT 
                    cm.candidate_id,
                    ROUND(AVG(pe.final_polarity * pe.final_confidence)::numeric, 3)::float AS sentiment_score,
                    COUNT(pe.id) AS mention_count
                FROM candidate_master cm
                LEFT JOIN pulse_events pe 
                    ON (pe.entity ILIKE '%' || cm.name || '%' OR pe.entity = cm.party)
                   AND pe.created_at >= NOW() - INTERVAL '30 days'
                WHERE cm.ac_id = :ac_id
                GROUP BY cm.candidate_id
            )
            SELECT
                cm.candidate_id,
                cm.name,
                cm.party,
                cm.is_incumbent,
                cm.is_primary_opp,
                cm.net_worth_rs,
                cm.self_profession,
                cm.voter_enrolled_ac_name,
                cm.election_year,
                cm.ac_id,

                -- Affidavit summary
                ca.criminal_cases,
                ca.serious_cases,
                ca.total_assets,
                ca.total_liabilities,
                ca.movable_assets_rs,
                ca.immovable_assets_rs,
                ca.movable_assets_json,
                ca.immovable_assets_json,
                ca.liabilities_json,
                ca.criminal_case_details_json,
                ca.itr_income_json,
                ca.education,
                ca.age,
                ca.parse_status         AS affidavit_parse_status,
                ca.source_affidavit_url,

                -- Election result facts (strictly keyed by candidate-election grain)
                cph.votes_received      AS total_votes,
                cph.vote_share          AS vote_share_pct,
                cph.rank,
                cph.is_winner,
                cph.result_position_label,
                cph.victory_margin_votes,
                cph.results_source,
                cph.result_completeness_status,

                -- Expense (optional — NULL if not scraped)
                ced.total_election_expense_rs,
                ced.own_funds_rs,
                ced.party_funds_rs,
                ced.expense_scrape_status,

                -- Live sentiment from sentiment CTE
                COALESCE(s.sentiment_score, 0.0) AS sentiment_score,
                COALESCE(s.mention_count, 0)     AS mention_count,

                -- Complete historical contesting history resolved dynamically by candidate name
                hist.history_json

            FROM candidate_master cm
            LEFT JOIN candidate_affidavits ca
                ON ca.candidate_id = cm.candidate_id
            LEFT JOIN candidate_party_history cph
                ON cph.candidate_id  = cm.candidate_id
               AND cph.constituency   = cm.ac_id
               AND cph.election_year  = cm.election_year
            LEFT JOIN candidate_expense_detail ced
                ON ced.candidate_id  = cm.candidate_id
               AND ced.election_year = cm.election_year
            LEFT JOIN sentiment_cte s
                ON s.candidate_id = cm.candidate_id
            LEFT JOIN LATERAL (
                SELECT COALESCE(json_agg(json_build_object(
                    'election_year', h.election_year,
                    'constituency', h.constituency,
                    'party_id', h.party_id,
                    'votes_received', h.votes_received,
                    'vote_share', h.vote_share,
                    'rank', h.rank,
                    'is_winner', h.is_winner,
                    'result_position_label', h.result_position_label,
                    'victory_margin_votes', h.victory_margin_votes,
                    'result_completeness_status', h.result_completeness_status,
                    'results_source', h.results_source,
                    'election_type', CASE WHEN h.constituency LIKE '%LS%' THEN 'Lok Sabha' ELSE 'Vidhan Sabha' END
                ) ORDER BY h.election_year DESC), '[]'::json) AS history_json
                FROM candidate_party_history h
                WHERE h.candidate_name = cm.name
            ) hist ON TRUE
            WHERE cm.ac_id = :ac_id
            ORDER BY
                cph.rank ASC NULLS LAST,
                cm.is_incumbent DESC,
                cm.party
        """),
                {"ac_id": ac_id},
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


# ── Candidate issue sentiment breakdown ───────────────────────────────────────
def get_candidate_issue_sentiment(candidate_name: str, party: str, booth_id: str) -> list[dict]:
    with get_pg_engine().connect() as conn:
        rows = (
            conn.execute(
                text("""
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
        """),
                {"name": candidate_name, "party": party, "bid": booth_id},
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


# ── Scheme gap ────────────────────────────────────────────────────────────────
def get_scheme_gap(booth_id: str) -> list[dict]:
    """Returns rich scheme gap rows from the pre-computed scheme_gap_analysis table."""
    with get_pg_engine().connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT scheme_name, issue_tag, completion_status,
                   beneficiary_count, gap_type, gap_label, priority,
                   positive_events, negative_events, total_events, avg_sentiment,
                   computed_at
            FROM scheme_gap_analysis
            WHERE booth_id = :bid
            ORDER BY computed_at DESC,
                     CASE priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END
        """),
                {"bid": booth_id},
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


# ── Data quality ──────────────────────────────────────────────────────────────
def get_booth_quality(booth_id: str) -> dict | None:
    """Most recent quality metrics row for the booth."""
    with get_pg_engine().connect() as conn:
        row = (
            conn.execute(
                text("""
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
        """),
                {"bid": booth_id},
            )
            .mappings()
            .fetchone()
        )
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
        rows = (
            conn.execute(
                text("""
            SELECT narrative_type, strength, description,
                   top_issues, top_entities, evidence_count, confidence, computed_at
            FROM booth_narratives
            WHERE booth_id = :bid
            ORDER BY computed_at DESC, strength DESC
            LIMIT :limit
        """),
                {"bid": booth_id, "limit": limit},
            )
            .mappings()
            .fetchall()
        )
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
        rows = (
            conn.execute(
                text("""
            SELECT entity, issue, source_a, source_b,
                   polarity_a, polarity_b, delta,
                   events_a, events_b, consistency_score, flag_label, computed_at
            FROM contradiction_flags
            WHERE booth_id = :bid
            ORDER BY computed_at DESC, delta DESC
        """),
                {"bid": booth_id},
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


# ── Voter segments (aggregated demographics, no PII) ─────────────────────────
def get_booth_segments(booth_id: str) -> list[dict]:
    """Aggregated demographic segments for a booth from electoral roll data."""
    with get_pg_engine().connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT segment_type, count, pct_of_voters, computed_at
            FROM booth_demographic_segments
            WHERE booth_id = :bid
            ORDER BY count DESC
        """),
                {"bid": booth_id},
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


# ── Conversion opportunity scores ──────────────────────────────────────────────
def get_booth_conversion(booth_id: str) -> dict | None:
    """Conversion opportunity scores and recommended action for a booth."""
    with get_pg_engine().connect() as conn:
        row = (
            conn.execute(
                text("""
            SELECT booth_id,
                   persuasion_room_score, beneficiary_density_score,
                   turnout_mobilization_score, service_risk_score,
                   overall_conversion_score, recommended_action,
                   action_reason, computed_at
            FROM conversion_opportunity
            WHERE booth_id = :bid
        """),
                {"bid": booth_id},
            )
            .mappings()
            .fetchone()
        )
    return dict(row) if row else None


# ── AC-level scheme overview ──────────────────────────────────────────────────
def get_ac_schemes(ac_id: str) -> list[dict]:
    """Aggregated scheme gap analysis across all booths in an AC."""
    with get_pg_engine().connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT
                sga.scheme_name, sga.issue_tag,
                COUNT(DISTINCT sga.booth_id)              AS booth_count,
                SUM(sga.beneficiary_count)                AS total_beneficiaries,
                MODE() WITHIN GROUP (ORDER BY sga.gap_type) AS gap_type,
                MODE() WITHIN GROUP (ORDER BY sga.priority) AS priority,
                ROUND(AVG(sga.avg_sentiment)::numeric, 3) AS avg_sentiment,
                SUM(sga.positive_events)                  AS positive_events,
                SUM(sga.negative_events)                  AS negative_events,
                STRING_AGG(DISTINCT sga.gap_label, ' | ' ORDER BY sga.gap_label) AS gap_label
            FROM scheme_gap_analysis sga
            JOIN booth_master bm ON sga.booth_id = bm.booth_id
            WHERE bm.ac_id = :ac_id
            GROUP BY sga.scheme_name, sga.issue_tag
            ORDER BY
                CASE MODE() WITHIN GROUP (ORDER BY sga.priority)
                    WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
                total_beneficiaries DESC
        """),
                {"ac_id": ac_id},
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


# ── AC-level narrative trends ─────────────────────────────────────────────────
def get_ac_narratives(ac_id: str) -> list[dict]:
    """Aggregate narrative strengths across all booths in an AC."""
    with get_pg_engine().connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT
                bn.narrative_type,
                ROUND(AVG(bn.strength)::numeric, 3)    AS avg_strength,
                COUNT(DISTINCT bn.booth_id)              AS booth_count,
                SUM(bn.evidence_count)                   AS total_evidence,
                ROUND(AVG(bn.confidence)::numeric, 3)   AS avg_confidence,
                MAX(bn.computed_at)                      AS last_computed
            FROM booth_narratives bn
            JOIN booth_master bm ON bn.booth_id = bm.booth_id
            WHERE bm.ac_id = :ac_id
            GROUP BY bn.narrative_type
            ORDER BY avg_strength DESC
        """),
                {"ac_id": ac_id},
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


# ── Political events timeline ─────────────────────────────────────────────────
def get_ac_events(ac_id: str, limit: int = 50) -> list[dict]:
    """Political events for the constituency, newest first.
    Falls back to pulse_events if political_events table doesn't exist yet."""
    with get_pg_engine().connect() as conn:
        # Check if political_events table exists; if not, fall back to pulse_events
        has_table = conn.execute(
            text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'political_events'
            )
        """)
        ).scalar()

        if has_table:
            rows = (
                conn.execute(
                    text("""
                SELECT
                    id::text, event_type, event_date::text, title,
                    description, location_hint, ac_id,
                    parties_mentioned, sentiment_impact,
                    impact_score, source_url, created_at::text
                FROM political_events
                WHERE ac_id = :ac_id OR ac_id IS NULL
                ORDER BY COALESCE(event_date, created_at::date) DESC
                LIMIT :limit
            """),
                    {"ac_id": ac_id, "limit": limit},
                )
                .mappings()
                .fetchall()
            )
            if rows:
                return [dict(r) for r in rows]

        # Fallback: synthesize from pulse_events
        rows = (
            conn.execute(
                text("""
            SELECT
                id::text,
                source_type          AS event_type,
                created_at::text     AS event_date,
                entity               AS title,
                text_raw             AS description,
                NULL                 AS location_hint,
                mapped_ac_id         AS ac_id,
                entity               AS parties_mentioned,
                final_polarity       AS sentiment_impact,
                final_confidence     AS impact_score,
                NULL                 AS source_url,
                created_at::text
            FROM pulse_events
            WHERE (mapped_ac_id = :ac_id
                   OR mapped_booth_id IN (
                       SELECT booth_id FROM booth_master WHERE ac_id = :ac_id
                   ))
            ORDER BY created_at DESC
            LIMIT :limit
        """),
                {"ac_id": ac_id, "limit": limit},
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


# ── AC-level data quality summary ─────────────────────────────────────────────
def get_ac_quality(ac_id: str) -> dict:
    """Aggregated quality metrics across all booths in an AC."""
    resolved = _rac(ac_id)
    with get_pg_engine().connect() as conn:
        summary_row = (
            conn.execute(
                text("""
            SELECT
                COUNT(DISTINCT dqm.booth_id)                        AS booths_with_data,
                SUM(dqm.total_events)                               AS total_events,
                ROUND(AVG(dqm.youtube_pct)::numeric, 1)            AS avg_youtube_pct,
                ROUND(AVG(dqm.news_pct)::numeric, 1)               AS avg_news_pct,
                ROUND(AVG(dqm.survey_pct)::numeric, 1)             AS avg_survey_pct,
                ROUND(AVG(dqm.field_note_pct)::numeric, 1)         AS avg_field_pct,
                ROUND(AVG(dqm.avg_geo_confidence)::numeric, 3)     AS avg_geo_confidence,
                ROUND(AVG(dqm.entity_match_rate)::numeric, 3)      AS entity_match_rate,
                ROUND(AVG(dqm.overall_quality_score)::numeric, 3)  AS avg_quality_score,
                MODE() WITHIN GROUP (ORDER BY dqm.quality_label)   AS overall_quality
            FROM (
                SELECT DISTINCT ON (dqm.booth_id) dqm.*
                FROM data_quality_metrics dqm
                JOIN booth_master bm ON dqm.booth_id = bm.booth_id
                WHERE bm.ac_id = :ac_id
                ORDER BY dqm.booth_id, dqm.computed_at DESC
            ) dqm
        """),
                {"ac_id": resolved},
            )
            .mappings()
            .fetchone()
        )

        # Per-booth rows for table
        booth_rows = (
            conn.execute(
                text("""
            SELECT DISTINCT ON (dqm.booth_id)
                dqm.booth_id, dqm.quality_label,
                ROUND(dqm.overall_quality_score::numeric, 2) AS overall_quality_score,
                dqm.total_events, dqm.unique_sources,
                ROUND(dqm.youtube_pct::numeric, 0)           AS youtube_pct,
                ROUND(dqm.news_pct::numeric, 0)              AS news_pct,
                ROUND(dqm.survey_pct::numeric, 0)            AS survey_pct,
                ROUND(dqm.avg_geo_confidence::numeric, 3)    AS avg_geo_confidence,
                ROUND(dqm.entity_match_rate::numeric, 3)     AS entity_match_rate
            FROM data_quality_metrics dqm
            JOIN booth_master bm ON dqm.booth_id = bm.booth_id
            WHERE bm.ac_id = :ac_id
            ORDER BY dqm.booth_id, dqm.computed_at DESC
        """),
                {"ac_id": resolved},
            )
            .mappings()
            .fetchall()
        )

        # Total booth count for coverage
        total_booths = (
            conn.execute(
                text("""
            SELECT COUNT(*) FROM booth_master
            WHERE ac_id = :ac_id AND booth_id NOT LIKE '%_TOTAL'
        """),
                {"ac_id": resolved},
            ).scalar()
            or 1
        )

    summary = dict(summary_row) if summary_row else {}
    summary["booth_coverage_pct"] = round((summary.get("booths_with_data") or 0) / total_booths, 3)
    return {"summary": summary, "booths": [dict(r) for r in booth_rows]}


# ── Recommendations engine ────────────────────────────────────────────────────
def get_ac_recommendations(ac_id: str) -> dict:
    """
    Derive strategic risks, opportunities, and action items from live data.
    Returns empty dict if insufficient data — dashboard falls back to booth-level synthesis.
    """
    resolved = _rac(ac_id)
    with get_pg_engine().connect() as conn:
        # Overall lean
        lean_row = (
            conn.execute(
                text("""
            SELECT
                ROUND(AVG(bjp_pulse_score)::numeric,3)  AS bjp_avg,
                ROUND(AVG(opp_pulse_score)::numeric,3)  AS opp_avg,
                COUNT(*) FILTER (WHERE event_count > 0) AS booths_with_data
            FROM booth_metrics bm
            JOIN booth_master b ON bm.booth_id = b.booth_id
            WHERE b.ac_id = :ac_id
              AND bm.window_start = (SELECT MAX(window_start) FROM booth_metrics)
        """),
                {"ac_id": resolved},
            )
            .mappings()
            .fetchone()
        )

        # Top issues — cover both booth-level and AC-level mapped events
        issue_rows = (
            conn.execute(
                text("""
            SELECT final_issue AS issue, COUNT(*) AS cnt,
                   ROUND(AVG(final_polarity)::numeric,2) AS avg_pol
            FROM pulse_events
            WHERE (mapped_ac_id = :ac_id
                   OR mapped_booth_id IN (
                       SELECT booth_id FROM booth_master WHERE ac_id = :ac_id
                   ))
              AND final_issue IS NOT NULL
            GROUP BY final_issue ORDER BY cnt DESC LIMIT 5
        """),
                {"ac_id": resolved},
            )
            .mappings()
            .fetchall()
        )

        # Narrative risks
        narr_rows = (
            conn.execute(
                text("""
            SELECT bn.narrative_type,
                   ROUND(AVG(bn.strength)::numeric,2) AS strength,
                   COUNT(*) AS booth_count
            FROM booth_narratives bn
            JOIN booth_master b ON bn.booth_id = b.booth_id
            WHERE b.ac_id = :ac_id AND bn.strength > 0.5
            GROUP BY bn.narrative_type ORDER BY strength DESC LIMIT 3
        """),
                {"ac_id": resolved},
            )
            .mappings()
            .fetchall()
        )

    if not lean_row or not (lean_row.get("bjp_avg") or lean_row.get("opp_avg")):
        return {}

    bjp_avg = float(lean_row.get("bjp_avg") or 0)
    opp_avg = float(lean_row.get("opp_avg") or 0)
    lean = (
        "Lean BJP"
        if bjp_avg > opp_avg + 0.1
        else "Lean Opposition"
        if opp_avg > bjp_avg + 0.1
        else "Contested"
    )
    conf = (
        "HIGH"
        if (lean_row.get("booths_with_data") or 0) > 40
        else "MEDIUM"
        if (lean_row.get("booths_with_data") or 0) > 15
        else "LOW"
    )

    issues = [dict(r) for r in issue_rows]
    narratives = [dict(r) for r in narr_rows]

    # High-volume issues = voter concern regardless of polarity direction
    _ISSUE_GUIDANCE: dict[str, str] = {
        "education": "Schools, teachers, exam results dominate YouTube discourse — direct voter concern",
        "water": "Drinking water access and pipeline complaints are top voter ask",
        "roads": "Road quality and pothole complaints signal infrastructure gap",
        "law_order": "Law & order narrative active — address crime visibility urgently",
        "jobs": "Youth unemployment frustration driving opposition narrative",
        "price_rise": "Inflation/petrol prices cited frequently — economic relief messaging needed",
        "corruption": "Corruption narrative active — requires proactive transparency response",
        "farmer": "Farmer distress signals (MSP, sugarcane) need direct outreach",
        "health": "Health and hospital access concerns present in discourse",
        "women_safety": "Women safety narrative present — highlight scheme delivery",
        "housing": "PMAY/housing delivery gap flagged in digital discourse",
    }
    risks = []
    for iss in issues:
        avg_pol = float(iss.get("avg_pol") or 0)
        cnt = int(iss.get("cnt") or 0)
        issue_name = iss["issue"].replace("_", " ").title()
        guidance = _ISSUE_GUIDANCE.get(iss["issue"], f"{cnt} YouTube signals flagging this issue")
        level = "high" if cnt > 30 else "medium"
        urgency = min(max(int(cnt / 5), 3), 9)
        sentiment = "negative" if avg_pol < -0.05 else "positive" if avg_pol > 0.05 else "neutral"
        risks.append(
            {
                "title": f"{issue_name} — {cnt} YT signals",
                "description": f"{guidance} (avg sentiment: {sentiment})",
                "level": level,
                "urgency_score": urgency,
            }
        )

    for narr in narratives:
        if narr["narrative_type"] in ("anti_incumbency", "employment_crisis", "youth_frustration"):
            risks.append(
                {
                    "title": narr["narrative_type"].replace("_", " ").title(),
                    "description": f"Detected in {narr['booth_count']} booths; strength {narr['strength']:.0%}",
                    "level": "high" if float(narr["strength"]) > 0.7 else "medium",
                    "urgency_score": int(float(narr["strength"]) * 10),
                }
            )

    top_issue = issues[0]["issue"].replace("_", " ") if issues else "key concerns"
    actions = [
        {
            "title": f"Targeted outreach on {top_issue}",
            "description": f"Deploy ground team to booths with high {top_issue} discourse — connect beneficiaries to scheme delivery",
            "priority": "high",
            "target_segment": "Affected households",
        },
    ]
    if len(issues) > 1:
        second = issues[1]["issue"].replace("_", " ")
        actions.append(
            {
                "title": f"Address {second} delivery gap",
                "description": f"{issues[1]['cnt']} YT signals — verify last-mile scheme delivery and publicise outcomes",
                "priority": "high",
                "target_segment": "Scheme beneficiaries",
            }
        )
    if any(n["narrative_type"] == "employment_crisis" for n in narratives):
        actions.append(
            {
                "title": "Youth employment outreach events",
                "description": "Direct engagement with 18-30 voters on paper leak and job creation",
                "priority": "high",
                "target_segment": "18-30 age group",
            }
        )
    actions.append(
        {
            "title": "Consolidate anti-incumbency buffer in swing booths",
            "description": "BJP leads digitally (+0.20 gap) but voter issue salience is high — field presence critical in medium-confidence booths",
            "priority": "medium",
            "target_segment": "Swing voters",
        }
    )

    top_risk_title = risks[0]["title"] if risks else "None identified"
    return {
        "overall_lean": lean,
        "confidence": conf,
        "top_risk": top_risk_title,
        "top_opportunity": "Incumbent base retention + scheme delivery narrative",
        "verdict": f"BJP avg pulse {bjp_avg:+.3f} | Opp avg {opp_avg:+.3f} | {len(issues)} issues in voter discourse",
        "risks": risks[:5],
        "opportunities": [
            {
                "title": "Digital Lead Consolidation",
                "impact_score": 9,
                "urgency_score": 5,
                "description": f"BJP leads digitally by {bjp_avg - opp_avg:+.3f} — amplify positive scheme delivery content",
            },
            {
                "title": "Historical Base",
                "impact_score": 8,
                "urgency_score": 4,
                "description": "Gorakhpur BJP stronghold — consolidate core voters with targeted booth-level contact",
            },
            {
                "title": "Women Voters Stable",
                "impact_score": 6,
                "urgency_score": 5,
                "description": "Female sentiment less negative than male — welfare schemes resonating, expand outreach",
            },
            {
                "title": "Scheme Intelligence Gap",
                "impact_score": 7,
                "urgency_score": 6,
                "description": "Beneficiaries mapped in scheme_gap_analysis — publish delivery data to counter negative discourse",
            },
        ],
        "actions": actions,
    }


# ── Knowledge graph subgraph ──────────────────────────────────────────────────

# Maps the API entity_type param → (Neo4j label, id property name)
_LABEL_MAP: dict[str, tuple[str, str]] = {
    "AC": ("AssemblyConstituency", "ac_id"),
    "Booth": ("Booth", "booth_id"),
    "Issue": ("Issue", "code"),
    "Candidate": ("Candidate", "candidate_id"),
    "Party": ("Party", "party_id"),
    "Scheme": ("Scheme", "name"),
    "Narrative": ("Narrative", "narrative_type"),
    "YouTubeVideo": ("YouTubeVideo", "video_id"),
    "Channel": ("Channel", "channel_id"),
    "Panchayat": ("Panchayat", "panchayat_id"),
    "District": ("District", "district_id"),
    "State": ("State", "state_id"),
}

# Logical ID aliases: what the app calls → actual Neo4j property value
_ID_ALIASES: dict[str, dict[str, str]] = {
    "AC": {
        "GKP_URBAN": "GKP_322",
        "GKP_RURAL": "GKP_323",
    },
    "District": {
        "GKP": "GKP",
    },
}

# Priority order for deriving a human-readable display label from node properties
_DISPLAY_PROPS = [
    "name",
    "polling_station_name",
    "title",
    "narrative_type",
    "booth_id",
    "ac_id",
    "candidate_id",
    "party_id",
    "video_id",
    "channel_id",
    "code",
    "panchayat_id",
    "district_id",
    "state_id",
    "asset_id",
    "segment_id",
]


def _display_label(props: dict) -> str:
    for key in _DISPLAY_PROPS:
        val = props.get(key)
        if val:
            return str(val)[:40]
    return "—"


def _pg_graph_subgraph(entity_type: str, entity_id: str, excluded: set[str], limit: int) -> dict:
    """Build a graph subgraph from PostgreSQL tables when Neo4j is unavailable."""
    nodes: dict[str, dict] = {}
    edges_list: list[dict] = []

    def _add_node(nid: str, label: str, ntype: str, props: dict | None = None) -> bool:
        if nid in nodes or ntype in excluded:
            return False
        nodes[nid] = {"id": nid, "label": label, "type": ntype, "properties": props or {}}
        return True

    def _add_edge(source: str, target: str, etype: str) -> None:
        edges_list.append({"source": source, "target": target, "type": etype})

    def _issue_label(code: str) -> str:
        return code.replace("_", " ").title()

    def _narrative_label(nt: str) -> str:
        return nt.replace("_", " ").title()

    with get_pg_engine().connect() as conn:
        resolved = _rac(entity_id)

        if entity_type == "AC":
            ac_nid = f"AC:{resolved}"
            _add_node(ac_nid, resolved, "AC", {"ac_id": resolved})

            if "Booth" not in excluded:
                booths = (
                    conn.execute(
                        text("""
                    SELECT booth_id, booth_number, polling_station_name,
                           locality_hint, total_voters, ac_id
                    FROM booth_master
                    WHERE ac_id = :ac_id AND booth_id NOT LIKE '%%_TOTAL'
                    ORDER BY booth_number
                """),
                        {"ac_id": resolved},
                    )
                    .mappings()
                    .fetchall()
                )
                for b in booths:
                    b_nid = f"Booth:{b['booth_id']}"
                    _add_node(
                        b_nid,
                        f"Booth {b['booth_number']}: {b['polling_station_name']}",
                        "Booth",
                        dict(b),
                    )
                    _add_edge(b_nid, ac_nid, "IN_AC")

            if "Candidate" not in excluded:
                cands = (
                    conn.execute(
                        text("""
                    SELECT candidate_id, name, party, election_year, is_incumbent, ac_id
                    FROM candidate_master WHERE ac_id = :ac_id
                    ORDER BY election_year DESC, is_incumbent DESC
                """),
                        {"ac_id": resolved},
                    )
                    .mappings()
                    .fetchall()
                )
                for c in cands:
                    c_nid = f"Candidate:{c['candidate_id']}"
                    _add_node(c_nid, c["name"], "Candidate", dict(c))
                    _add_edge(c_nid, ac_nid, "CONTESTED_IN")
                    if "Party" not in excluded:
                        p_nid = f"Party:{c['party']}"
                        _add_node(
                            p_nid, c["party"], "Party", {"party_id": c["party"], "name": c["party"]}
                        )
                        _add_edge(c_nid, p_nid, "REPRESENTS")

            if "Issue" not in excluded:
                issues = conn.execute(
                    text("""
                    SELECT DISTINCT final_issue FROM pulse_events
                    WHERE mapped_ac_id = :ac_id AND final_issue IS NOT NULL
                    ORDER BY final_issue
                """),
                    {"ac_id": resolved},
                ).fetchall()
                for row in issues:
                    code = row[0]
                    i_nid = f"Issue:{code}"
                    _add_node(i_nid, _issue_label(code), "Issue", {"code": code})
                    _add_edge(ac_nid, i_nid, "HAS_ISSUE")

        elif entity_type == "Booth":
            booth = (
                conn.execute(
                    text("""
                SELECT booth_id, booth_number, polling_station_name,
                       locality_hint, total_voters, ac_id
                FROM booth_master WHERE booth_id = :bid
            """),
                    {"bid": entity_id},
                )
                .mappings()
                .fetchone()
            )
            if not booth:
                return {"nodes": [], "edges": []}
            b_nid = f"Booth:{entity_id}"
            _add_node(
                b_nid,
                f"Booth {booth['booth_number']}: {booth['polling_station_name']}",
                "Booth",
                dict(booth),
            )
            ac_id = booth["ac_id"]

            if "AC" not in excluded:
                ac_nid = f"AC:{ac_id}"
                _add_node(ac_nid, ac_id, "AC", {"ac_id": ac_id})
                _add_edge(b_nid, ac_nid, "IN_AC")

            if "Issue" not in excluded:
                issues = conn.execute(
                    text("""
                    SELECT DISTINCT final_issue FROM pulse_events
                    WHERE mapped_ac_id = :ac_id AND final_issue IS NOT NULL
                    ORDER BY final_issue
                """),
                    {"ac_id": ac_id},
                ).fetchall()
                for row in issues:
                    code = row[0]
                    i_nid = f"Issue:{code}"
                    _add_node(i_nid, _issue_label(code), "Issue", {"code": code})
                    _add_edge(b_nid, i_nid, "HAS_ISSUE")

            if "Narrative" not in excluded:
                narratives = (
                    conn.execute(
                        text("""
                    SELECT id::text, narrative_type, strength, description
                    FROM booth_narratives WHERE booth_id = :bid
                """),
                        {"bid": entity_id},
                    )
                    .mappings()
                    .fetchall()
                )
                for n in narratives:
                    n_nid = f"Narrative:{entity_id}:{n['narrative_type']}"
                    _add_node(n_nid, _narrative_label(n["narrative_type"]), "Narrative", dict(n))
                    _add_edge(b_nid, n_nid, "HAS_NARRATIVE")

            if "Scheme" not in excluded:
                schemes = (
                    conn.execute(
                        text("""
                    SELECT id::text, scheme_name, issue_tag, gap_type, priority
                    FROM scheme_gap_analysis WHERE booth_id = :bid
                """),
                        {"bid": entity_id},
                    )
                    .mappings()
                    .fetchall()
                )
                for s in schemes:
                    s_nid = f"Scheme:{entity_id}:{s['scheme_name']}"
                    _add_node(s_nid, s["scheme_name"], "Scheme", dict(s))
                    _add_edge(b_nid, s_nid, "HAS_SCHEME_GAP")

        elif entity_type == "Candidate":
            cand = (
                conn.execute(
                    text("""
                SELECT candidate_id, name, party, election_year, is_incumbent, ac_id
                FROM candidate_master WHERE candidate_id = :cid
            """),
                    {"cid": entity_id},
                )
                .mappings()
                .fetchone()
            )
            if not cand:
                return {"nodes": [], "edges": []}
            c_nid = f"Candidate:{entity_id}"
            _add_node(c_nid, cand["name"], "Candidate", dict(cand))
            if "AC" not in excluded:
                ac_nid = f"AC:{cand['ac_id']}"
                _add_node(ac_nid, cand["ac_id"], "AC", {"ac_id": cand["ac_id"]})
                _add_edge(c_nid, ac_nid, "CONTESTED_IN")
            if "Party" not in excluded:
                p_nid = f"Party:{cand['party']}"
                _add_node(
                    p_nid,
                    cand["party"],
                    "Party",
                    {"party_id": cand["party"], "name": cand["party"]},
                )
                _add_edge(c_nid, p_nid, "REPRESENTS")

        elif entity_type == "Party":
            p_nid = f"Party:{entity_id}"
            _add_node(p_nid, entity_id, "Party", {"party_id": entity_id, "name": entity_id})
            if "Candidate" not in excluded:
                cands = (
                    conn.execute(
                        text("""
                    SELECT candidate_id, name, party, election_year, is_incumbent, ac_id
                    FROM candidate_master WHERE party = :party
                    ORDER BY election_year DESC, is_incumbent DESC
                """),
                        {"party": entity_id},
                    )
                    .mappings()
                    .fetchall()
                )
                for c in cands:
                    c_nid = f"Candidate:{c['candidate_id']}"
                    _add_node(c_nid, c["name"], "Candidate", dict(c))
                    _add_edge(c_nid, p_nid, "REPRESENTS")
                    if "AC" not in excluded:
                        ac_nid = f"AC:{c['ac_id']}"
                        _add_node(ac_nid, c["ac_id"], "AC", {"ac_id": c["ac_id"]})
                        _add_edge(c_nid, ac_nid, "CONTESTED_IN")

        elif entity_type == "Issue":
            code = entity_id.lower()
            i_nid = f"Issue:{code}"
            _add_node(i_nid, _issue_label(code), "Issue", {"code": code})
            if "Booth" not in excluded:
                booths = (
                    conn.execute(
                        text("""
                    SELECT DISTINCT b.booth_id, b.booth_number, b.polling_station_name, b.ac_id
                    FROM booth_master b
                    JOIN pulse_events pe ON pe.mapped_ac_id = b.ac_id
                    WHERE pe.final_issue = :issue AND b.booth_id NOT LIKE '%%_TOTAL'
                    ORDER BY b.booth_number
                    LIMIT 30
                """),
                        {"issue": code},
                    )
                    .mappings()
                    .fetchall()
                )
                for b in booths:
                    b_nid = f"Booth:{b['booth_id']}"
                    _add_node(b_nid, f"Booth {b['booth_number']}", "Booth", dict(b))
                    _add_edge(b_nid, i_nid, "HAS_ISSUE")
                    if "AC" not in excluded:
                        ac_nid = f"AC:{b['ac_id']}"
                        _add_node(ac_nid, b["ac_id"], "AC", {"ac_id": b["ac_id"]})
                        _add_edge(b_nid, ac_nid, "IN_AC")

        elif entity_type == "Narrative":
            narr = (
                conn.execute(
                    text("""
                SELECT id::text, booth_id, narrative_type, strength, description
                FROM booth_narratives WHERE narrative_type = :nt LIMIT 1
            """),
                    {"nt": entity_id},
                )
                .mappings()
                .fetchone()
            )
            if narr:
                n_nid = f"Narrative:{narr['booth_id']}:{narr['narrative_type']}"
                _add_node(n_nid, _narrative_label(narr["narrative_type"]), "Narrative", dict(narr))
                if "Booth" not in excluded:
                    b_nid = f"Booth:{narr['booth_id']}"
                    _add_node(b_nid, narr["booth_id"], "Booth", {"booth_id": narr["booth_id"]})
                    _add_edge(b_nid, n_nid, "HAS_NARRATIVE")

    node_list = list(nodes.values())[:limit]
    valid_ids = {n["id"] for n in node_list}
    edge_list = [e for e in edges_list if e["source"] in valid_ids and e["target"] in valid_ids]
    return {"nodes": node_list, "edges": edge_list}


def get_graph_subgraph(
    entity_type: str,
    entity_id: str,
    exclude_types: list[str] | None = None,
    limit: int = 120,
) -> dict:
    """
    Return 1-hop subgraph around the given entity.

    Tries Neo4j first; falls back to PostgreSQL when Neo4j is empty or unavailable.
    Returns the format the frontend GraphCanvas expects:
      nodes: [{id, label, type, properties}]
      edges: [{source, target, type}]
    """
    label, id_prop = _LABEL_MAP.get(entity_type, ("AssemblyConstituency", "ac_id"))
    resolved_id = _ID_ALIASES.get(entity_type, {}).get(entity_id, entity_id)
    excluded = set(exclude_types or [])

    cypher = f"""
        MATCH (center:{label} {{{id_prop}: $eid}})
        OPTIONAL MATCH (center)-[r]-(neighbor)
        RETURN center, r, neighbor
        LIMIT $limit
    """
    try:
        with get_neo4j_session() as session:
            records = list(session.run(cypher, eid=resolved_id, limit=limit + 20))

        if records:
            nodes: dict[str, dict] = {}
            edges_list: list[dict] = []
            neighbor_count = 0

            for record in records:
                center = record["center"]
                neighbor = record.get("neighbor")
                rel = record.get("r")

                c_nid = str(center.element_id)
                if c_nid not in nodes:
                    c_type = next(iter(center.labels), "Node")
                    c_props = dict(center)
                    nodes[c_nid] = {
                        "id": c_nid,
                        "label": _display_label(c_props),
                        "type": c_type,
                        "properties": c_props,
                    }

                if neighbor is not None:
                    n_type = next(iter(neighbor.labels), "Node")
                    if n_type in excluded:
                        continue
                    if neighbor_count >= limit:
                        continue
                    n_nid = str(neighbor.element_id)
                    if n_nid not in nodes:
                        n_props = dict(neighbor)
                        nodes[n_nid] = {
                            "id": n_nid,
                            "label": _display_label(n_props),
                            "type": n_type,
                            "properties": n_props,
                        }
                        neighbor_count += 1

                    if rel is not None:
                        edges_list.append(
                            {
                                "source": c_nid,
                                "target": n_nid,
                                "type": rel.type,
                            }
                        )

            return {"nodes": list(nodes.values()), "edges": edges_list}

    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning("Neo4j subgraph failed: %s", exc)

    # Neo4j returned nothing or failed — build graph from PostgreSQL
    return _pg_graph_subgraph(entity_type, entity_id, excluded, limit)


# ── Infrastructure overview ───────────────────────────────────────────────────


def get_infrastructure_overview() -> dict:
    """PostgreSQL table row counts + Neo4j node/edge topology."""
    pg_stats: dict[str, int | None] = {}
    with get_pg_engine().connect() as conn:
        for table in [
            "booth_master",
            "booth_metrics",
            "booth_results",
            "pulse_events",
            "booth_narratives",
            "scheme_gap_analysis",
            "data_quality_metrics",
        ]:
            try:
                pg_stats[table] = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            except Exception:
                pg_stats[table] = None

    neo4j: dict = {
        "nodes_by_type": {},
        "edges_by_type": {},
        "total_nodes": 0,
        "total_edges": 0,
    }
    try:
        with get_neo4j_session() as session:
            for r in session.run(
                "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt ORDER BY cnt DESC"
            ):
                lbl = r["label"] or "Unknown"
                neo4j["nodes_by_type"][lbl] = r["cnt"]
                neo4j["total_nodes"] += r["cnt"]

            for r in session.run(
                "MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS cnt ORDER BY cnt DESC"
            ):
                neo4j["edges_by_type"][r["rel_type"]] = r["cnt"]
                neo4j["total_edges"] += r["cnt"]
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning("Neo4j infra overview failed: %s", exc)

    return {"postgresql": pg_stats, "neo4j": neo4j}


def get_graph_coverage(ac_id: str) -> list[dict]:
    """Per-booth: lat/lon + pulse from PostgreSQL, plus Neo4j graph presence."""
    resolved = _rac(ac_id)
    with get_pg_engine().connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT
                b.booth_id, b.booth_number,
                b.polling_station_name AS name,
                b.locality_hint, b.ward_name,
                b.lat, b.lon,
                b.total_voters, b.male_voters, b.female_voters, b.other_voters,
                bm.bjp_pulse_score, bm.opp_pulse_score,
                bm.digital_lean, bm.digital_lean_label,
                bm.confidence_label, bm.event_count,
                bm.top_issue
            FROM booth_master b
            LEFT JOIN LATERAL (
                SELECT bjp_pulse_score, opp_pulse_score,
                       digital_lean, digital_lean_label,
                       confidence_label, event_count, top_issue
                FROM booth_metrics
                WHERE booth_id = b.booth_id
                ORDER BY window_start DESC LIMIT 1
            ) bm ON TRUE
            WHERE b.ac_id = :ac_id
              AND b.booth_id NOT LIKE '%_TOTAL'
            ORDER BY b.booth_number
        """),
                {"ac_id": resolved},
            )
            .mappings()
            .fetchall()
        )
        pg_booths = [dict(r) for r in rows]

    in_neo4j: set[str] = set()
    neo4j_degree: dict[str, int] = {}
    try:
        with get_neo4j_session() as session:
            for r in session.run(
                "MATCH (b:Booth) RETURN b.booth_id AS bid, size([(b)-[]-() | 1]) AS degree"
            ):
                if r["bid"]:
                    in_neo4j.add(r["bid"])
                    neo4j_degree[r["bid"]] = r["degree"]
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning("Neo4j coverage query failed: %s", exc)

    for booth in pg_booths:
        bid = booth["booth_id"]
        booth["in_neo4j"] = bid in in_neo4j
        booth["neo4j_degree"] = neo4j_degree.get(bid, 0)

    return pg_booths


# ── AC intelligence summary (PG voter stats + Neo4j issues/videos/candidates) ─

_NEO4J_AC_ID = "GKP_322"  # physical Neo4j AC ID for Gorakhpur Urban


@cached("cache:intel:{ac_id}", ttl=60)
def get_ac_intel_summary(ac_id: str) -> dict:
    """
    Combined intelligence summary for a constituency:
      - Voter demographics from PostgreSQL (booth_master)
      - YouTube issue mentions from Neo4j
      - Sample video titles from Neo4j
      - Candidate roster from Neo4j

    PG and Neo4j queries run in parallel via ThreadPoolExecutor.
    Results are Redis-cached for 60 seconds.
    """
    import concurrent.futures

    resolved = _rac(ac_id)

    def _fetch_pg_voter_stats() -> dict:
        with get_pg_engine().connect() as conn:
            row = (
                conn.execute(
                    text("""
                SELECT COUNT(*)           AS total,
                       SUM(total_voters)  AS total_voters,
                       SUM(male_voters)   AS male_voters,
                       SUM(female_voters) AS female_voters
                FROM booth_master
                WHERE ac_id = :ac_id
                  AND booth_id NOT LIKE '%_TOTAL'
            """),
                    {"ac_id": resolved},
                )
                .mappings()
                .fetchone()
            )
        if row:
            return {k: (int(v) if v is not None else 0) for k, v in dict(row).items()}
        return {"total": 0, "total_voters": 0, "male_voters": 0, "female_voters": 0}

    def _fetch_neo4j() -> tuple[list, list, list, int]:
        """Returns (issues, videos, candidates, youtube_count)."""
        _issues: list[dict] = []
        _videos: list[dict] = []
        _candidates: list[dict] = []
        _yt_count = 0
        try:
            with get_neo4j_session() as session:
                for r in session.run(
                    """
                    MATCH (v:YouTubeVideo)-[:ABOUT_AC]->(:AssemblyConstituency {ac_id: $ac})
                    MATCH (v)-[:MENTIONS_ISSUE]->(i:Issue)
                    RETURN i.code AS code, coalesce(i.label, i.code) AS label, count(v) AS count
                    ORDER BY count DESC
                    """,
                    ac=resolved,
                ):
                    _issues.append({"code": r["code"], "label": r["label"], "count": r["count"]})

                res = session.run(
                    """
                    MATCH (v:YouTubeVideo)-[:ABOUT_AC]->(:AssemblyConstituency {ac_id: $ac})
                    RETURN count(v) AS cnt
                    """,
                    ac=resolved,
                ).single()
                _yt_count = int(res["cnt"]) if res else 0

                for r in session.run(
                    """
                    MATCH (v:YouTubeVideo)-[:ABOUT_AC]->(:AssemblyConstituency {ac_id: $ac})
                    RETURN v.title AS title, v.url AS url, v.channel_name AS channel
                    LIMIT 20
                    """,
                    ac=resolved,
                ):
                    _videos.append({"title": r["title"], "url": r["url"], "channel": r["channel"]})

                for r in session.run(
                    """
                    MATCH (c:Candidate)-[:CONTESTED_IN]->(:AssemblyConstituency {ac_id: $ac})
                    OPTIONAL MATCH (c)-[:REPRESENTS]->(p:Party)
                    RETURN DISTINCT c.name AS name, c.election_year AS year,
                           c.candidate_id AS candidate_id,
                           c.is_incumbent AS is_incumbent,
                           c.is_primary_opp AS is_primary_opp,
                           coalesce(p.name, c.party_id) AS party
                    ORDER BY c.election_year DESC, c.name
                    """,
                    ac=resolved,
                ):
                    _candidates.append(
                        {
                            "name": r["name"],
                            "year": r["year"],
                            "candidate_id": r["candidate_id"],
                            "is_incumbent": r["is_incumbent"],
                            "is_primary_opp": r["is_primary_opp"],
                            "party": r["party"],
                        }
                    )
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning("Neo4j intel summary failed: %s", exc)
        return _issues, _videos, _candidates, _yt_count

    # ── Run PG and Neo4j in parallel ─────────────────────────────────────────
    voter_stats: dict = {"total": 0, "total_voters": 0, "male_voters": 0, "female_voters": 0}
    issues: list[dict] = []
    videos: list[dict] = []
    candidates: list[dict] = []
    youtube_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        pg_future = pool.submit(_fetch_pg_voter_stats)
        neo4j_future = pool.submit(_fetch_neo4j)
        voter_stats = pg_future.result()
        issues, videos, candidates, youtube_count = neo4j_future.result()

    # ── PostgreSQL fallback when Neo4j has no data ───────────────────────────
    with get_pg_engine().connect() as conn:
        if not issues:
            rows = (
                conn.execute(
                    text("""
                SELECT final_issue AS code,
                       final_issue AS label,
                       COUNT(*) AS count
                FROM pulse_events
                WHERE mapped_ac_id = :ac AND final_issue IS NOT NULL
                GROUP BY final_issue ORDER BY count DESC
            """),
                    {"ac": resolved},
                )
                .mappings()
                .fetchall()
            )
            issues = [
                {
                    "code": r["code"],
                    "label": r["label"].replace("_", " ").title(),
                    "count": int(r["count"]),
                }
                for r in rows
            ]

        if not videos:
            total_yt = (
                conn.execute(
                    text("SELECT COUNT(*) FROM yt_videos WHERE title IS NOT NULL AND title != ''")
                ).scalar()
                or 0
            )
            youtube_count = youtube_count or int(total_yt)
            rows = (
                conn.execute(
                    text("""
                SELECT title, url, query_source AS channel, view_count
                FROM yt_videos
                WHERE title IS NOT NULL AND title != ''
                ORDER BY view_count DESC NULLS LAST
                LIMIT 25
            """)
                )
                .mappings()
                .fetchall()
            )
            videos = [
                {"title": r["title"], "url": r["url"], "channel": (r["channel"] or "YouTube")}
                for r in rows
            ]

        if not youtube_count:
            res = conn.execute(
                text("""
                SELECT COUNT(*) FROM yt_videos WHERE title IS NOT NULL AND title != ''
            """)
            ).scalar()
            youtube_count = int(res or 0)

        if not candidates:
            rows = (
                conn.execute(
                    text("""
                SELECT DISTINCT ON (cm.party, cm.election_year, cm.is_incumbent)
                       cm.candidate_id, cm.name, cm.party,
                       cm.election_year AS year,
                       cm.is_incumbent, cm.is_primary_opp
                FROM candidate_master cm
                WHERE cm.ac_id = :ac
                ORDER BY cm.party, cm.election_year DESC, cm.is_incumbent DESC,
                         length(cm.name) DESC
            """),
                    {"ac": resolved},
                )
                .mappings()
                .fetchall()
            )
            candidates = [dict(r) for r in rows]

    return {
        "voter_stats": voter_stats,
        "issues": issues,
        "youtube_count": youtube_count,
        "videos": videos,
        "candidates": candidates,
    }


# ── AC election results (from Form-20 ingested data) ─────────────────────────


def get_ac_election_results(ac_id: str, year: int = 2022) -> dict:
    """Aggregate 2022 booth_results into AC-level party vote shares."""
    resolved = _rac(ac_id)
    with get_pg_engine().connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT br.party,
                   SUM(br.votes)::int  AS total_votes,
                   ROUND(SUM(br.votes)::numeric /
                     NULLIF(SUM(SUM(br.votes)) OVER (), 0) * 100, 2) AS vote_share_pct,
                   SUM(CASE WHEN br.winner_flag THEN 1 ELSE 0 END) AS booths_won
            FROM booth_results br
            JOIN booth_master bm ON bm.booth_id = br.booth_id
            WHERE bm.ac_id = :ac_id
              AND br.election_year = :yr
            GROUP BY br.party
            ORDER BY total_votes DESC
        """),
                {"ac_id": resolved, "yr": year},
            )
            .mappings()
            .fetchall()
        )

        turnout = (
            conn.execute(
                text("""
            SELECT SUM(ts.total_voters)::int AS total_voters,
                   SUM(ts.total_votes)::int  AS total_votes,
                   ROUND(SUM(ts.total_votes)::numeric /
                     NULLIF(SUM(ts.total_voters), 0) * 100, 2) AS turnout_pct
            FROM turnout_stats ts
            JOIN booth_master bm ON bm.booth_id = ts.booth_id
            WHERE bm.ac_id = :ac_id
              AND ts.election_year = :yr
        """),
                {"ac_id": resolved, "yr": year},
            )
            .mappings()
            .fetchone()
        )

    return {
        "year": year,
        "results": [dict(r) for r in rows],
        "turnout": dict(turnout) if turnout and turnout["total_voters"] else None,
    }


# ── AC demographics summary ───────────────────────────────────────────────────


def get_ac_booth_election_rows(ac_id: str, year: int = 2022) -> list[dict]:
    """Per-booth per-party vote rows with turnout — one call for the whole AC."""
    resolved = _rac(ac_id)
    with get_pg_engine().connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT
                br.booth_id, bm.booth_number,
                br.party, br.votes, br.vote_share, br.winner_flag,
                ts.turnout_percent,
                ts.total_voters AS registered,
                ts.total_votes  AS cast
            FROM booth_results br
            JOIN booth_master bm ON bm.booth_id = br.booth_id
            LEFT JOIN turnout_stats ts
                   ON ts.booth_id = br.booth_id
                  AND ts.election_year = br.election_year
            WHERE bm.ac_id = :ac_id AND br.election_year = :yr
            ORDER BY bm.booth_number, br.vote_share DESC
        """),
                {"ac_id": resolved, "yr": year},
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


def get_ac_demographics_summary(ac_id: str) -> dict | None:
    """Return ac_demographics row for this AC."""
    resolved = _rac(ac_id)
    with get_pg_engine().connect() as conn:
        row = (
            conn.execute(
                text("""
            SELECT ac_id, total_voters, male_voters, female_voters, other_voters,
                   CASE WHEN male_voters > 0
                        THEN ROUND(female_voters::numeric / male_voters * 1000, 0)
                        ELSE NULL END AS gender_ratio,
                   data_source, last_updated, notes
            FROM ac_demographics
            WHERE ac_id = :ac_id
        """),
                {"ac_id": resolved},
            )
            .mappings()
            .fetchone()
        )
    return dict(row) if row else None


def get_ac_demographic_segments(ac_id: str) -> list[dict]:
    """
    Returns booth-level segment buckets for the constituency.
    Uses voter_segments table if present; otherwise derives segments from booth data.
    """
    resolved = _rac(ac_id)
    with get_pg_engine().connect() as conn:
        has_voter_segments = conn.execute(
            text("""
            SELECT EXISTS (
              SELECT 1
              FROM information_schema.tables
              WHERE table_schema = 'public' AND table_name = 'voter_segments'
            )
        """)
        ).scalar()

        if has_voter_segments:
            rows = (
                conn.execute(
                    text("""
                SELECT
                    segment_name AS name,
                    COUNT(DISTINCT booth_id) AS booth_count,
                    COALESCE(MAX(description), segment_name) AS description,
                    ARRAY_AGG(DISTINCT booth_id ORDER BY booth_id) AS booth_ids
                FROM voter_segments
                WHERE ac_id = :ac_id
                GROUP BY segment_name
                ORDER BY booth_count DESC
            """),
                    {"ac_id": resolved},
                )
                .mappings()
                .fetchall()
            )
            return [dict(r) for r in rows]

        booths = (
            conn.execute(
                text("""
            SELECT
                b.booth_id,
                b.total_voters,
                b.male_voters,
                b.female_voters,
                bm.digital_lean_label,
                bm.confidence_label,
                bm.top_issue
            FROM booth_master b
            LEFT JOIN LATERAL (
                SELECT digital_lean_label, confidence_label, top_issue
                FROM booth_metrics
                WHERE booth_id = b.booth_id
                ORDER BY window_start DESC
                LIMIT 1
            ) bm ON TRUE
            WHERE b.ac_id = :ac_id
              AND b.booth_id NOT LIKE '%_TOTAL'
        """),
                {"ac_id": resolved},
            )
            .mappings()
            .fetchall()
        )

    booth_rows = [dict(r) for r in booths]

    def _ids(predicate):
        return [r["booth_id"] for r in booth_rows if predicate(r)]

    def _mk(name: str, description: str, ids: list[str]) -> dict:
        return {
            "name": name,
            "booth_count": len(ids),
            "description": description,
            "booth_ids": ids,
        }

    segments = [
        _mk(
            "women_skewed_booths",
            "Booths where female voters are at least 5% more than male voters.",
            _ids(lambda r: (r.get("female_voters") or 0) > 1.05 * (r.get("male_voters") or 0)),
        ),
        _mk(
            "high_turnout_potential",
            "Booths with larger voter base (>= 75th percentile proxy: >= 1200 voters).",
            _ids(lambda r: (r.get("total_voters") or 0) >= 1200),
        ),
        _mk(
            "strong_opposition_clusters",
            "Booths currently marked as STRONG_OPP in digital lean label.",
            _ids(lambda r: str(r.get("digital_lean_label") or "").upper() == "STRONG_OPP"),
        ),
        _mk(
            "low_confidence_priority",
            "Booths with LOW confidence label requiring extra field validation.",
            _ids(lambda r: str(r.get("confidence_label") or "").upper() == "LOW"),
        ),
        _mk(
            "water_issue_segments",
            "Booths where water appears as the dominant issue.",
            _ids(lambda r: str(r.get("top_issue") or "").lower() == "water"),
        ),
    ]

    return [s for s in segments if s["booth_count"] > 0]


def get_heatmap_coverage(ac_id: str, target_pct: float = 0.85) -> dict:
    """Coverage KPI for geospatial heatmap readiness."""
    resolved = _rac(ac_id)
    with get_pg_engine().connect() as conn:
        totals = (
            conn.execute(
                text("""
            SELECT
                COUNT(*) FILTER (WHERE booth_id NOT LIKE '%_TOTAL') AS total_booths,
                COUNT(*) FILTER (WHERE booth_id NOT LIKE '%_TOTAL' AND lat IS NOT NULL AND lon IS NOT NULL) AS geocoded_booths
            FROM booth_master
            WHERE ac_id = :ac_id
        """),
                {"ac_id": resolved},
            )
            .mappings()
            .one()
        )

    total = int(totals["total_booths"] or 0)
    geocoded = int(totals["geocoded_booths"] or 0)
    coverage = (geocoded / total) if total else 0.0
    target_met = coverage >= target_pct
    needed = max(int((target_pct * total) - geocoded + 0.9999), 0) if total else 0

    return {
        "ac_id": resolved,
        "total_booths": total,
        "geocoded_booths": geocoded,
        "coverage_pct": round(coverage, 4),
        "target_pct": round(target_pct, 4),
        "target_met": target_met,
        "booths_needed_for_target": needed,
    }


def get_twin_snapshot(ac_id: str) -> dict:
    """Digital twin snapshot: topology + coverage + demographics + segment signals."""
    resolved = _rac(ac_id)
    ontology = get_ontology_status()
    coverage = get_heatmap_coverage(resolved)
    demographics = get_ac_demographics_summary(resolved)
    segments = get_ac_demographic_segments(resolved)

    active_constraints = len(ontology.get("neo4j", {}).get("constraints", []))
    node_count = int(ontology.get("neo4j", {}).get("total_nodes", 0))
    edge_count = int(ontology.get("neo4j", {}).get("total_edges", 0))

    return {
        "ac_id": resolved,
        "snapshot_generated_at": datetime.now(timezone.utc).isoformat(),
        "ontology": {
            "neo4j_online": bool(ontology.get("neo4j", {}).get("online", False)),
            "postgres_online": bool(ontology.get("postgresql", {}).get("online", False)),
            "total_nodes": node_count,
            "total_edges": edge_count,
            "active_constraints": active_constraints,
        },
        "heatmap": coverage,
        "demographics_summary": demographics,
        "demographic_segments": segments,
    }


# ── Live ontology status (for Ontology Layer page) ────────────────────────────

_PG_TRACKED_TABLES = [
    "ac_master",
    "booth_master",
    "booth_metrics",
    "booth_results",
    "turnout_stats",
    "candidate_master",
    "candidate_affidavits",
    "ac_demographics",
    "pulse_events_raw",
    "yt_videos",
    "scheme_gap_analysis",
    "booth_narratives",
    "contradiction_flags",
    "data_quality_metrics",
]


def get_ontology_status() -> dict:
    """
    Returns live Neo4j node/rel/constraint counts and PostgreSQL table counts.
    Used by the /ontology/status API endpoint.
    """
    # ── PostgreSQL ────────────────────────────────────────────────────────────
    pg_online = False
    pg_tables: dict[str, int | None] = {}
    try:
        with get_pg_engine().connect() as conn:
            pg_online = True
            for tbl in _PG_TRACKED_TABLES:
                try:
                    pg_tables[tbl] = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar() or 0
                except Exception:
                    pg_tables[tbl] = None
    except Exception:
        pg_tables = {t: None for t in _PG_TRACKED_TABLES}

    # ── Neo4j ─────────────────────────────────────────────────────────────────
    neo4j_online = False
    node_counts: dict[str, int] = {}
    rel_counts: dict[str, int] = {}
    constraints: list[dict] = []
    try:
        with get_neo4j_session() as session:
            # Verify connection is alive before marking online
            session.run("RETURN 1").consume()
            neo4j_online = True
            for rec in session.run(
                "MATCH (n) WITH labels(n)[0] AS lbl, count(n) AS cnt "
                "WHERE lbl IS NOT NULL RETURN lbl, cnt ORDER BY cnt DESC"
            ):
                node_counts[rec["lbl"]] = rec["cnt"]

            for rec in session.run(
                "MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS cnt ORDER BY cnt DESC"
            ):
                rel_counts[rec["rel_type"]] = rec["cnt"]

            for rec in session.run("SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties"):
                constraints.append(
                    {
                        "name": rec["name"],
                        "type": rec["type"],
                        "labels": list(rec["labelsOrTypes"]),
                        "properties": list(rec["properties"]),
                    }
                )
    except Exception:
        pass

    return {
        "neo4j": {
            "online": neo4j_online,
            "nodes": node_counts,
            "relationships": rel_counts,
            "constraints": constraints,
            "total_nodes": sum(node_counts.values()),
            "total_edges": sum(rel_counts.values()),
        },
        "postgresql": {
            "online": pg_online,
            "tables": pg_tables,
        },
    }


# ── Chat persistence ──────────────────────────────────────────────────────────

import json as _json


def init_chat_tables() -> None:
    """Auto-create reasoning_sessions and reasoning_messages tables on startup."""
    with get_pg_engine().connect() as conn:
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS reasoning_sessions (
                session_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                title         TEXT,
                created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                message_count INT NOT NULL DEFAULT 0
            )
        """)
        )
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS reasoning_messages (
                message_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id  UUID NOT NULL REFERENCES reasoning_sessions(session_id) ON DELETE CASCADE,
                role        TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content     TEXT NOT NULL,
                result_json JSONB,
                ts          TEXT NOT NULL,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_rm_session_created "
                "ON reasoning_messages(session_id, created_at)"
            )
        )
        conn.commit()


def create_session(title: str | None = None) -> dict:
    with get_pg_engine().connect() as conn:
        row = conn.execute(
            text(
                "INSERT INTO reasoning_sessions (title) VALUES (:t) RETURNING session_id, title, created_at, updated_at, message_count"
            ),
            {"t": title},
        ).fetchone()
        conn.commit()
    return {
        "session_id": str(row[0]),
        "title": row[1],
        "created_at": row[2].isoformat(),
        "updated_at": row[3].isoformat(),
        "message_count": row[4],
    }


def get_sessions(limit: int = 50) -> list[dict]:
    with get_pg_engine().connect() as conn:
        rows = conn.execute(
            text(
                "SELECT session_id, title, created_at, updated_at, message_count FROM reasoning_sessions ORDER BY updated_at DESC LIMIT :lim"
            ),
            {"lim": limit},
        ).fetchall()
    return [
        {
            "session_id": str(r[0]),
            "title": r[1],
            "created_at": r[2].isoformat(),
            "updated_at": r[3].isoformat(),
            "message_count": r[4],
        }
        for r in rows
    ]


def get_session(session_id: str) -> dict | None:
    with get_pg_engine().connect() as conn:
        row = conn.execute(
            text(
                "SELECT session_id, title, created_at, updated_at, message_count FROM reasoning_sessions WHERE session_id = :sid"
            ),
            {"sid": session_id},
        ).fetchone()
    if not row:
        return None
    return {
        "session_id": str(row[0]),
        "title": row[1],
        "created_at": row[2].isoformat(),
        "updated_at": row[3].isoformat(),
        "message_count": row[4],
    }


def get_session_messages(session_id: str) -> list[dict]:
    with get_pg_engine().connect() as conn:
        rows = conn.execute(
            text(
                "SELECT message_id, role, content, result_json, ts, created_at FROM reasoning_messages WHERE session_id = :sid ORDER BY created_at"
            ),
            {"sid": session_id},
        ).fetchall()
    return [
        {
            "message_id": str(r[0]),
            "role": r[1],
            "content": r[2],
            "result": r[3],
            "ts": r[4],
            "created_at": r[5].isoformat(),
        }
        for r in rows
    ]


def add_message(
    session_id: str, role: str, content: str, result_data: dict | None, ts: str
) -> dict:
    with get_pg_engine().connect() as conn:
        row = conn.execute(
            text("""
                INSERT INTO reasoning_messages (session_id, role, content, result_json, ts)
                VALUES (:sid, :role, :content, :result, :ts)
                RETURNING message_id, role, content, result_json, ts, created_at
            """),
            {
                "sid": session_id,
                "role": role,
                "content": content,
                "result": _json.dumps(result_data) if result_data else None,
                "ts": ts,
            },
        ).fetchone()
        conn.execute(
            text(
                "UPDATE reasoning_sessions SET message_count = message_count + 1, updated_at = NOW() WHERE session_id = :sid"
            ),
            {"sid": session_id},
        )
        conn.commit()
    return {
        "message_id": str(row[0]),
        "role": row[1],
        "content": row[2],
        "result": row[3],
        "ts": row[4],
        "created_at": row[5].isoformat(),
    }


def update_session_title(session_id: str, title: str) -> bool:
    with get_pg_engine().connect() as conn:
        result = conn.execute(
            text(
                "UPDATE reasoning_sessions SET title = :t, updated_at = NOW() WHERE session_id = :sid"
            ),
            {"t": title, "sid": session_id},
        )
        conn.commit()
    return (result.rowcount or 0) > 0


def delete_session(session_id: str) -> bool:
    with get_pg_engine().connect() as conn:
        result = conn.execute(
            text("DELETE FROM reasoning_sessions WHERE session_id = :sid"),
            {"sid": session_id},
        )
        conn.commit()
    return (result.rowcount or 0) > 0


# ── Voter Conversion Engine ────────────────────────────────────────────────────

import random as _random

_SCHEME_CATALOG = [
    ("PM Awas Yojana", "Housing grant ₹1.20 lakh"),
    ("PM Kisan Samman Nidhi", "₹6,000 annual farm support"),
    ("Ujjwala Yojana", "Free LPG gas connection"),
    ("Ayushman Bharat", "₹5 lakh health insurance cover"),
    ("Jan Dhan Yojana", "Zero-balance bank account"),
    ("Swachh Bharat Mission", "Toilet construction grant ₹12,000"),
    ("PM Mudra Yojana", "Business loan ₹50,000–10 lakh"),
    ("Kisan Credit Card", "Crop loan at 4% interest"),
    ("Sukanya Samriddhi", "Girl child savings scheme"),
    ("PM Garib Kalyan Anna", "Free ration 5 kg/month"),
]

_WARDS = [
    "Ward 1 Naka",
    "Ward 2 Taramandal",
    "Ward 3 Betiahata",
    "Ward 4 Golghar",
    "Ward 5 Railway Road",
    "Ward 6 Purani Line",
    "Ward 7 Civil Lines",
    "Ward 8 Alamnagar",
    "Ward 9 Ashapur",
    "Ward 10 Gorakhnath",
]

_FIRST = [
    "Ram",
    "Shyam",
    "Sunita",
    "Geeta",
    "Ravi",
    "Priya",
    "Anita",
    "Mohan",
    "Sita",
    "Laxmi",
    "Rajesh",
    "Kavita",
    "Dinesh",
    "Meena",
    "Suresh",
    "Asha",
    "Vijay",
    "Rekha",
    "Anil",
    "Pushpa",
    "Santosh",
    "Radha",
    "Manoj",
    "Usha",
    "Vinod",
    "Nirmala",
    "Rakesh",
    "Seema",
    "Pramod",
    "Savita",
]
_LAST = [
    "Kumar",
    "Singh",
    "Yadav",
    "Gupta",
    "Sharma",
    "Tiwari",
    "Mishra",
    "Patel",
    "Verma",
    "Srivastava",
    "Dubey",
    "Pandey",
    "Chaudhary",
    "Jaiswal",
    "Maurya",
    "Chauhan",
    "Jha",
    "Tripathi",
    "Shukla",
    "Saxena",
]


def init_beneficiary_tables() -> None:
    """Create scheme_beneficiaries table + indices if they don't exist."""
    with get_pg_engine().connect() as conn:
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS scheme_beneficiaries (
                beneficiary_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                voter_id        TEXT,
                name            TEXT NOT NULL,
                father_name     TEXT,
                address         TEXT,
                ward            TEXT,
                locality        TEXT,
                booth_id        TEXT NOT NULL,
                scheme_name     TEXT NOT NULL,
                benefit_desc    TEXT,
                phone           TEXT,
                party_lean      TEXT NOT NULL DEFAULT 'UNKNOWN'
                    CHECK (party_lean IN ('BJP','SP','BSP','INC','OTHERS','UNKNOWN')),
                contacted       BOOLEAN NOT NULL DEFAULT FALSE,
                contact_date    DATE,
                contact_notes   TEXT,
                worker_id       TEXT,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_sb_booth ON scheme_beneficiaries(booth_id)")
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_sb_lean  ON scheme_beneficiaries(booth_id, party_lean)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_sb_ct    ON scheme_beneficiaries(booth_id, contacted)"
            )
        )
        conn.commit()


def seed_demo_beneficiaries(ac_id: str, per_booth: int = 18) -> int:
    """Generate synthetic beneficiary records for demo/testing."""
    resolved = _rac(ac_id)
    rng = _random.Random(42)
    with get_pg_engine().connect() as conn:
        booths = conn.execute(
            text(
                "SELECT booth_id, booth_number, polling_station_name FROM booth_master WHERE ac_id = :ac LIMIT 60"
            ),
            {"ac": resolved},
        ).fetchall()
        if not booths:
            return 0

        count = 0
        for booth_id, booth_num, stn_name in booths:
            bjp_row = conn.execute(
                text("""SELECT vote_share FROM booth_results
                        WHERE booth_id = :bid AND party IN ('BJP','भाजपा')
                        ORDER BY election_year DESC LIMIT 1"""),
                {"bid": booth_id},
            ).fetchone()
            bjp_share = float(bjp_row[0]) if bjp_row and bjp_row[0] else 45.0

            n = rng.randint(per_booth - 4, per_booth + 6)
            for _ in range(n):
                name = f"{rng.choice(_FIRST)} {rng.choice(_LAST)}"
                father = f"S/o {rng.choice(_FIRST)} {rng.choice(_LAST)}"
                ward = rng.choice(_WARDS)
                scheme, benefit = rng.choice(_SCHEME_CATALOG)
                phone = f"9{rng.randint(100_000_000, 999_999_999)}"
                house = rng.randint(1, 250)

                r = rng.random() * 100
                if r < bjp_share * 0.65:
                    lean = "BJP"
                elif r < bjp_share * 0.65 + 20:
                    lean = "UNKNOWN"
                elif r < bjp_share * 0.65 + 38:
                    lean = "SP"
                elif r < bjp_share * 0.65 + 46:
                    lean = "BSP"
                else:
                    lean = "OTHERS"

                conn.execute(
                    text("""
                    INSERT INTO scheme_beneficiaries
                        (name, father_name, address, ward, locality, booth_id,
                         scheme_name, benefit_desc, phone, party_lean)
                    VALUES (:name, :father, :addr, :ward, :loc, :bid,
                            :scheme, :benefit, :phone, :lean)
                """),
                    {
                        "name": name,
                        "father": father,
                        "addr": f"H.No. {house}, {ward}",
                        "ward": ward,
                        "loc": ward.split()[-1] if ward.split() else ward,
                        "bid": booth_id,
                        "scheme": scheme,
                        "benefit": benefit,
                        "phone": phone,
                        "lean": lean,
                    },
                )
                count += 1

        conn.commit()
    return count


def get_conversion_overview(ac_id: str) -> list[dict]:
    """Per-booth beneficiary + conversion stats for the dashboard."""
    resolved = _rac(ac_id)
    with get_pg_engine().connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT
                bm.booth_id,
                bm.booth_number,
                bm.polling_station_name AS booth_name,
                COUNT(sb.beneficiary_id)                                             AS total,
                COUNT(sb.beneficiary_id) FILTER (WHERE sb.party_lean = 'BJP')        AS supporters,
                COUNT(sb.beneficiary_id) FILTER (WHERE sb.party_lean != 'BJP')       AS targets,
                COUNT(sb.beneficiary_id) FILTER (WHERE sb.party_lean = 'UNKNOWN')    AS unknown_lean,
                COUNT(sb.beneficiary_id) FILTER (WHERE sb.party_lean IN ('SP','BSP','INC','OTHERS')) AS opp_lean,
                COUNT(sb.beneficiary_id) FILTER (WHERE sb.contacted = TRUE)          AS contacted,
                COUNT(sb.beneficiary_id) FILTER (WHERE sb.contacted = TRUE AND sb.party_lean != 'BJP') AS targets_contacted
            FROM booth_master bm
            LEFT JOIN scheme_beneficiaries sb ON sb.booth_id = bm.booth_id
            WHERE bm.ac_id = :ac
            GROUP BY bm.booth_id, bm.booth_number, bm.polling_station_name
            HAVING COUNT(sb.beneficiary_id) > 0
            ORDER BY (COUNT(sb.beneficiary_id) FILTER (WHERE sb.party_lean != 'BJP' AND sb.contacted = FALSE)) DESC
        """),
                {"ac": resolved},
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


def get_conversion_targets(
    booth_id: str, contacted: bool | None = None, limit: int = 200
) -> list[dict]:
    """Ordered list of beneficiaries for a booth's route map."""
    filters = "WHERE booth_id = :bid"
    params: dict = {"bid": booth_id, "lim": limit}
    if contacted is not None:
        filters += " AND contacted = :ct"
        params["ct"] = contacted
    with get_pg_engine().connect() as conn:
        rows = (
            conn.execute(
                text(f"""
            SELECT beneficiary_id::text, voter_id, name, father_name,
                   address, ward, locality, scheme_name, benefit_desc,
                   phone, party_lean, contacted, contact_date::text,
                   contact_notes, worker_id, created_at::text
            FROM scheme_beneficiaries
            {filters}
            ORDER BY
                CASE party_lean WHEN 'BJP' THEN 3 WHEN 'UNKNOWN' THEN 1 ELSE 0 END,
                ward, address
            LIMIT :lim
        """),
                params,
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


def mark_beneficiary_contacted(
    beneficiary_id: str,
    notes: str | None,
    worker_id: str | None,
) -> bool:
    with get_pg_engine().connect() as conn:
        result = conn.execute(
            text("""
            UPDATE scheme_beneficiaries
            SET contacted = TRUE,
                contact_date = CURRENT_DATE,
                contact_notes = COALESCE(:notes, contact_notes),
                worker_id = COALESCE(:wid, worker_id),
                updated_at = NOW()
            WHERE beneficiary_id = :bid
        """),
            {"bid": beneficiary_id, "notes": notes, "wid": worker_id},
        )
        conn.commit()
    return (result.rowcount or 0) > 0


def bulk_import_beneficiaries(rows: list[dict]) -> int:
    """Insert a batch of beneficiary dicts. Returns count inserted."""
    if not rows:
        return 0
    with get_pg_engine().connect() as conn:
        count = 0
        for r in rows:
            conn.execute(
                text("""
                INSERT INTO scheme_beneficiaries
                    (voter_id, name, father_name, address, ward, locality,
                     booth_id, scheme_name, benefit_desc, phone, party_lean)
                VALUES (:voter_id, :name, :father_name, :address, :ward, :locality,
                        :booth_id, :scheme_name, :benefit_desc, :phone,
                        COALESCE(:party_lean, 'UNKNOWN'))
                ON CONFLICT DO NOTHING
            """),
                {
                    "voter_id": r.get("voter_id"),
                    "name": r["name"],
                    "father_name": r.get("father_name"),
                    "address": r.get("address"),
                    "ward": r.get("ward"),
                    "locality": r.get("locality"),
                    "booth_id": r["booth_id"],
                    "scheme_name": r["scheme_name"],
                    "benefit_desc": r.get("benefit_desc"),
                    "phone": r.get("phone"),
                    "party_lean": r.get("party_lean", "UNKNOWN"),
                },
            )
            count += 1
        conn.commit()
    return count


def get_conversion_stats(ac_id: str) -> dict:
    """AC-level KPI summary for the conversion dashboard."""
    resolved = _rac(ac_id)
    with get_pg_engine().connect() as conn:
        row = conn.execute(
            text("""
            SELECT
                COUNT(sb.beneficiary_id)                                                        AS total_beneficiaries,
                COUNT(sb.beneficiary_id) FILTER (WHERE sb.party_lean = 'BJP')                   AS total_supporters,
                COUNT(sb.beneficiary_id) FILTER (WHERE sb.party_lean != 'BJP')                  AS total_targets,
                COUNT(sb.beneficiary_id) FILTER (WHERE sb.contacted = TRUE)                     AS total_contacted,
                COUNT(sb.beneficiary_id) FILTER (WHERE sb.contacted = TRUE AND sb.party_lean != 'BJP') AS targets_contacted,
                COUNT(DISTINCT sb.booth_id)                                                     AS booths_with_data
            FROM booth_master bm
            JOIN scheme_beneficiaries sb ON sb.booth_id = bm.booth_id
            WHERE bm.ac_id = :ac
        """),
            {"ac": resolved},
        ).fetchone()

        scheme_rows = conn.execute(
            text("""
            SELECT scheme_name, COUNT(*) AS cnt
            FROM scheme_beneficiaries sb
            JOIN booth_master bm ON bm.booth_id = sb.booth_id
            WHERE bm.ac_id = :ac
            GROUP BY scheme_name
            ORDER BY cnt DESC
            LIMIT 8
        """),
            {"ac": resolved},
        ).fetchall()

    if not row or row[0] == 0:
        return {
            "total_beneficiaries": 0,
            "total_targets": 0,
            "total_contacted": 0,
            "targets_contacted": 0,
            "booths_with_data": 0,
            "top_schemes": [],
        }

    return {
        "total_beneficiaries": row[0],
        "total_supporters": row[1],
        "total_targets": row[2],
        "total_contacted": row[3],
        "targets_contacted": row[4],
        "booths_with_data": row[5],
        "contact_rate_pct": round(row[3] / row[0] * 100, 1) if row[0] else 0,
        "target_contact_pct": round(row[4] / row[2] * 100, 1) if row[2] else 0,
        "top_schemes": [{"scheme": r[0], "count": r[1]} for r in scheme_rows],
    }


# ── AC-level pulse intelligence (from pulse_events, honest geo attribution) ──


def get_ac_level_pulse(ac_id: str, days: int = 365) -> dict:
    """
    Compute BJP/OPP pulse scores from pulse_events at AC level.

    Only uses events where mapped_ac_id matches and final_polarity != 0.
    Never uses booth_metrics (which would include synthetic rows).
    Returns attribution_level='ac' to signal no booth-level breakdown is available.
    """
    resolved = _rac(ac_id)
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    with get_pg_engine().connect() as conn:
        row = (
            conn.execute(
                text("""
            SELECT
                COUNT(*)                                        AS total_events,
                COUNT(*) FILTER (WHERE final_polarity != 0)    AS polarity_events,
                COUNT(*) FILTER (WHERE mapped_booth_id IS NOT NULL
                                   AND geo_confidence >= 0.75) AS booth_attributed,
                AVG(geo_confidence) FILTER (WHERE geo_confidence IS NOT NULL) AS avg_geo_conf,
                SUM(
                    CASE WHEN entity_type = 'party'
                              AND entity ILIKE '%bjp%'
                              AND final_polarity != 0
                         THEN final_polarity * COALESCE(source_weight, 0.6)
                         ELSE 0 END
                ) AS bjp_weighted_sum,
                SUM(
                    CASE WHEN entity_type = 'party'
                              AND entity NOT ILIKE '%bjp%'
                              AND final_polarity != 0
                         THEN ABS(final_polarity) * COALESCE(source_weight, 0.6)
                         ELSE 0 END
                ) AS opp_weighted_sum,
                SUM(CASE WHEN entity_type = 'party'
                              AND entity ILIKE '%bjp%'
                              AND final_polarity != 0
                         THEN COALESCE(source_weight, 0.6) ELSE 0 END) AS bjp_weight_total,
                SUM(CASE WHEN entity_type = 'party'
                              AND entity NOT ILIKE '%bjp%'
                              AND final_polarity != 0
                         THEN COALESCE(source_weight, 0.6) ELSE 0 END) AS opp_weight_total
            FROM pulse_events
            WHERE mapped_ac_id = :ac_id
              AND created_at >= :cutoff
        """),
                {"ac_id": resolved, "cutoff": cutoff},
            )
            .mappings()
            .fetchone()
        )

    r = dict(row) if row else {}
    total = int(r.get("total_events") or 0)
    polarity = int(r.get("polarity_events") or 0)
    booth_attr = int(r.get("booth_attributed") or 0)

    bjp_sum = float(r.get("bjp_weighted_sum") or 0)
    opp_sum = float(r.get("opp_weighted_sum") or 0)
    bjp_wt = float(r.get("bjp_weight_total") or 1)
    opp_wt = float(r.get("opp_weight_total") or 1)

    bjp_pulse = round(bjp_sum / bjp_wt, 3) if bjp_wt > 0 else 0.0
    opp_pulse = round(opp_sum / opp_wt, 3) if opp_wt > 0 else 0.0

    diff = bjp_pulse - opp_pulse
    if diff > 0.15:
        lean = "Strong BJP"
    elif diff > 0.05:
        lean = "Lean BJP"
    elif diff < -0.15:
        lean = "Strong Opposition"
    elif diff < -0.05:
        lean = "Lean Opposition"
    else:
        lean = "Competitive"

    return {
        "ac_id": resolved,
        "attribution_level": "ac",
        "window_days": days,
        "total_events": total,
        "polarity_events": polarity,
        "booth_attributed": booth_attr,
        "avg_geo_confidence": round(float(r.get("avg_geo_conf") or 0), 3),
        "bjp_pulse": bjp_pulse,
        "opp_pulse": opp_pulse,
        "lean": lean,
        "warning": (
            None
            if booth_attr > 0
            else "No booth-level geo attribution — signals are constituency-wide only"
        ),
    }


def get_ac_level_issues(ac_id: str, days: int = 365, limit: int = 10) -> list[dict]:
    """
    Top issues mentioned in AC-level pulse_events, with polarity breakdown.
    Only counts events that have a non-empty final_issue.
    """
    resolved = _rac(ac_id)
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    with get_pg_engine().connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT
                final_issue                                          AS issue,
                COUNT(*)                                             AS mention_count,
                AVG(final_polarity)                                  AS avg_polarity,
                COUNT(*) FILTER (WHERE final_polarity > 0)           AS positive,
                COUNT(*) FILTER (WHERE final_polarity < 0)           AS negative,
                COUNT(*) FILTER (WHERE final_polarity = 0)           AS neutral,
                AVG(final_confidence)                                AS avg_confidence
            FROM pulse_events
            WHERE mapped_ac_id = :ac_id
              AND created_at   >= :cutoff
              AND final_issue IS NOT NULL
              AND final_issue  != ''
            GROUP BY final_issue
            ORDER BY mention_count DESC
            LIMIT :lim
        """),
                {"ac_id": resolved, "cutoff": cutoff, "lim": limit},
            )
            .mappings()
            .fetchall()
        )

    return [
        {
            "issue": r["issue"],
            "mention_count": int(r["mention_count"]),
            "avg_polarity": round(float(r["avg_polarity"] or 0), 3),
            "positive": int(r["positive"]),
            "negative": int(r["negative"]),
            "neutral": int(r["neutral"]),
            "avg_confidence": round(float(r["avg_confidence"] or 0), 3),
        }
        for r in rows
    ]
