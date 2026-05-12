-- =============================================================================
-- Migration 005: political_events table + data_quality_metrics full schema
-- Run: psql $POSTGRES_URL -f db/migrations/005_political_events.sql
-- =============================================================================

-- ── 1. POLITICAL EVENTS ───────────────────────────────────────────────────────
-- Structured political events (rallies, arrests, scheme launches, incidents)
-- Sourced from: news NLP extraction, manual entry, press releases

CREATE TABLE IF NOT EXISTS political_events (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type          VARCHAR(50) NOT NULL,   -- rally | arrest | scheme_launch | controversy | election_result
    event_date          DATE,
    title               TEXT        NOT NULL,
    description         TEXT,
    location_hint       VARCHAR(200),
    ac_id               VARCHAR(30) REFERENCES ac_master(ac_id),
    parties_mentioned   TEXT,                   -- comma-separated party ids
    sentiment_impact    SMALLINT,               -- -1 | 0 | 1
    impact_score        FLOAT       DEFAULT 0.5,
    source_url          TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pol_events_ac   ON political_events(ac_id, event_date DESC);
CREATE INDEX IF NOT EXISTS idx_pol_events_type ON political_events(event_type);

-- ── 2. DATA QUALITY METRICS — ensure all columns exist ───────────────────────
-- Migration 002 may have created a partial schema; this adds missing columns
-- idempotently so running on a fresh or existing DB both work.

ALTER TABLE data_quality_metrics
    ADD COLUMN IF NOT EXISTS computed_at         TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS window_days         INTEGER     DEFAULT 7,
    ADD COLUMN IF NOT EXISTS total_events        INTEGER     DEFAULT 0,
    ADD COLUMN IF NOT EXISTS unique_sources      INTEGER     DEFAULT 0,
    ADD COLUMN IF NOT EXISTS youtube_pct         FLOAT       DEFAULT 0,
    ADD COLUMN IF NOT EXISTS news_pct            FLOAT       DEFAULT 0,
    ADD COLUMN IF NOT EXISTS survey_pct          FLOAT       DEFAULT 0,
    ADD COLUMN IF NOT EXISTS field_note_pct      FLOAT       DEFAULT 0,
    ADD COLUMN IF NOT EXISTS booth_mapped_pct    FLOAT       DEFAULT 0,
    ADD COLUMN IF NOT EXISTS ac_mapped_pct       FLOAT       DEFAULT 0,
    ADD COLUMN IF NOT EXISTS avg_geo_confidence  FLOAT       DEFAULT 0,
    ADD COLUMN IF NOT EXISTS avg_nlp_confidence  FLOAT       DEFAULT 0,
    ADD COLUMN IF NOT EXISTS llm_extracted_pct   FLOAT       DEFAULT 0,
    ADD COLUMN IF NOT EXISTS entity_match_rate   FLOAT       DEFAULT 0,
    ADD COLUMN IF NOT EXISTS missing_entity_pct  FLOAT       DEFAULT 0,
    ADD COLUMN IF NOT EXISTS source_diversity_score FLOAT   DEFAULT 0,
    ADD COLUMN IF NOT EXISTS overall_quality_score  FLOAT   DEFAULT 0,
    ADD COLUMN IF NOT EXISTS quality_label       VARCHAR(20) DEFAULT 'INSUFFICIENT',
    ADD COLUMN IF NOT EXISTS quality_reasons     JSONB       DEFAULT '[]';

-- ── 3. BOOTH NARRATIVES — ensure full schema ──────────────────────────────────
ALTER TABLE booth_narratives
    ADD COLUMN IF NOT EXISTS description   TEXT,
    ADD COLUMN IF NOT EXISTS top_issues    JSONB   DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS top_entities  JSONB   DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS evidence_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS confidence    FLOAT   DEFAULT 0,
    ADD COLUMN IF NOT EXISTS computed_at   TIMESTAMPTZ DEFAULT NOW();

-- ── 4. CONTRADICTION FLAGS — ensure full schema ───────────────────────────────
ALTER TABLE contradiction_flags
    ADD COLUMN IF NOT EXISTS issue             VARCHAR(50),
    ADD COLUMN IF NOT EXISTS events_a          INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS events_b          INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS consistency_score FLOAT   DEFAULT 0,
    ADD COLUMN IF NOT EXISTS flag_label        VARCHAR(30),
    ADD COLUMN IF NOT EXISTS computed_at       TIMESTAMPTZ DEFAULT NOW();

-- ── 5. SCHEME GAP ANALYSIS — ensure full schema ───────────────────────────────
ALTER TABLE scheme_gap_analysis
    ADD COLUMN IF NOT EXISTS issue_tag          VARCHAR(50),
    ADD COLUMN IF NOT EXISTS completion_status  VARCHAR(30),
    ADD COLUMN IF NOT EXISTS beneficiary_count  INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS gap_label          TEXT,
    ADD COLUMN IF NOT EXISTS positive_events    INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS negative_events    INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_events       INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS avg_sentiment      FLOAT   DEFAULT 0,
    ADD COLUMN IF NOT EXISTS computed_at        TIMESTAMPTZ DEFAULT NOW();
