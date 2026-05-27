-- =============================================================================
-- Migration 012: Composite indexes on pulse_events + pulse_events_raw
--   and candidate deduplication (fixes #11 and #3 from bottleneck audit)
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- PART A: Composite indexes for pulse_events_raw / pulse_events
-- Queries on these tables always filter by (ac_id/mapped_ac_id, booth_id, event_type)
-- ─────────────────────────────────────────────────────────────────────────────

-- pulse_events_raw: main lookup path — by source_type and processing state
CREATE INDEX IF NOT EXISTS idx_per_source_type_processed
    ON pulse_events_raw (source_type, processed, created_at DESC);

-- pulse_events (mapped/scored): used by AC-level aggregation queries
CREATE INDEX IF NOT EXISTS idx_pe_mapped_ac_issue
    ON pulse_events (mapped_ac_id, final_issue)
    WHERE final_issue IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_pe_mapped_ac_ts
    ON pulse_events (mapped_ac_id, created_at DESC);

-- booth_metrics: the LATERAL join in get_booths_for_ac hits this repeatedly
CREATE INDEX IF NOT EXISTS idx_booth_metrics_booth_window
    ON booth_metrics (booth_id, window_start DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- PART B: Candidate deduplication
-- Strategy: keep the row with the longest name (most descriptive) per
--   (ac_id, party, election_year, is_incumbent) group.
--   Duplicate rows were introduced by multiple ingestion passes creating
--   both GKP_322_<slug>_<year> and <NAME>_<year> candidate_ids.
-- ─────────────────────────────────────────────────────────────────────────────

-- Safety: backup before deduplication
CREATE TABLE IF NOT EXISTS candidate_master_dedup_backup AS
    SELECT * FROM candidate_master;

-- Delete duplicate rows, keeping the one with the longest candidate_id
-- (which is typically the slug-form with full context)
DELETE FROM candidate_master
WHERE ctid NOT IN (
    SELECT DISTINCT ON (ac_id, party, election_year, name)
        ctid
    FROM candidate_master
    ORDER BY
        ac_id, party, election_year, name,
        -- Prefer rows with richer candidate_id (slug form is longer)
        length(candidate_id) DESC
);

-- After dedup, add a unique partial index to prevent future duplicates
CREATE UNIQUE INDEX IF NOT EXISTS uq_candidate_master_core
    ON candidate_master (ac_id, party, election_year, name);

-- Partial index for fast incumbent lookups
CREATE INDEX IF NOT EXISTS idx_candidate_master_incumbent
    ON candidate_master (ac_id, election_year)
    WHERE is_incumbent = TRUE;
