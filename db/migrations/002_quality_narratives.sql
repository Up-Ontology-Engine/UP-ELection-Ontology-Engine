-- =============================================================================
-- Migration 002: Data Quality, Narratives, Contradictions, Scheme Gap Types
-- Run: psql $POSTGRES_URL -f db/migrations/002_quality_narratives.sql
-- =============================================================================

-- ── 1. DATA QUALITY METRICS ──────────────────────────────────────────────────
-- One row per booth per compute window. Answers: "how much can we trust this?"

CREATE TABLE IF NOT EXISTS data_quality_metrics (
    id                      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    booth_id                VARCHAR(40)  NOT NULL,
    computed_at             TIMESTAMPTZ  DEFAULT NOW(),
    window_days             INTEGER      DEFAULT 7,

    -- Volume
    total_events            INTEGER      DEFAULT 0,
    unique_sources          INTEGER      DEFAULT 0,   -- distinct source_type values

    -- Source composition (0-100 %)
    youtube_pct             FLOAT        DEFAULT 0,
    news_pct                FLOAT        DEFAULT 0,
    survey_pct              FLOAT        DEFAULT 0,
    field_note_pct          FLOAT        DEFAULT 0,

    -- Geo resolution quality
    booth_mapped_pct        FLOAT        DEFAULT 0,   -- % events mapped to booth level
    ac_mapped_pct           FLOAT        DEFAULT 0,   -- % mapped only to AC level
    avg_geo_confidence      FLOAT        DEFAULT 0,

    -- NLP quality
    avg_nlp_confidence      FLOAT        DEFAULT 0,
    llm_extracted_pct       FLOAT        DEFAULT 0,   -- % from LLM vs rule fallback
    entity_match_rate       FLOAT        DEFAULT 0,   -- % events with valid entity
    missing_entity_pct      FLOAT        DEFAULT 0,

    -- Final scores
    source_diversity_score  FLOAT        DEFAULT 0,   -- penalises single-source domination
    overall_quality_score   FLOAT        DEFAULT 0,   -- 0-1 composite
    quality_label           VARCHAR(20)  DEFAULT 'UNKNOWN',   -- HIGH/MEDIUM/LOW/INSUFFICIENT
    quality_reasons         JSONB        DEFAULT '[]',        -- ["Only YouTube data","30% AC-level"]

    CONSTRAINT uq_quality_booth_window UNIQUE (booth_id, computed_at)
);

CREATE INDEX IF NOT EXISTS idx_dqm_booth ON data_quality_metrics(booth_id, computed_at DESC);

-- ── 2. BOOTH NARRATIVES ───────────────────────────────────────────────────────
-- Detected narrative patterns per booth per window.

CREATE TABLE IF NOT EXISTS booth_narratives (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    booth_id        VARCHAR(40)  NOT NULL,
    computed_at     TIMESTAMPTZ  DEFAULT NOW(),
    window_days     INTEGER      DEFAULT 7,

    narrative_type  VARCHAR(50)  NOT NULL,
    -- development_positive | anti_incumbency | corruption_narrative |
    -- price_rise_narrative | women_safety_narrative | employment_crisis |
    -- scheme_success | swing_possible

    strength        FLOAT        DEFAULT 0,    -- 0-1 signal strength
    description     TEXT,                      -- human-readable "What the data says"
    top_issues      JSONB        DEFAULT '[]', -- ["water","jobs"]
    top_entities    JSONB        DEFAULT '[]', -- ["BJP","Yogi Adityanath"]
    evidence_count  INTEGER      DEFAULT 0,    -- # pulse events supporting this narrative
    confidence      FLOAT        DEFAULT 0,

    CONSTRAINT uq_narrative_booth_type UNIQUE (booth_id, narrative_type, computed_at)
);

CREATE INDEX IF NOT EXISTS idx_narratives_booth ON booth_narratives(booth_id, computed_at DESC);
CREATE INDEX IF NOT EXISTS idx_narratives_type  ON booth_narratives(narrative_type, strength DESC);

-- ── 3. CONTRADICTION FLAGS ────────────────────────────────────────────────────
-- Records per-entity signal conflicts between sources.

CREATE TABLE IF NOT EXISTS contradiction_flags (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    booth_id        VARCHAR(40)  NOT NULL,
    entity          VARCHAR(200) NOT NULL,
    issue           VARCHAR(50),
    computed_at     TIMESTAMPTZ  DEFAULT NOW(),
    window_days     INTEGER      DEFAULT 7,

    source_a        VARCHAR(30),   -- e.g. "youtube"
    source_b        VARCHAR(30),   -- e.g. "news"
    polarity_a      FLOAT,         -- avg polarity from source_a
    polarity_b      FLOAT,         -- avg polarity from source_b
    delta           FLOAT,         -- abs(polarity_a - polarity_b)
    events_a        INTEGER,
    events_b        INTEGER,
    consistency_score FLOAT,       -- 1=perfectly consistent, 0=completely contradictory
    flag_label      VARCHAR(30),   -- MIXED_SIGNALS | SWING_INDICATOR | MINOR_DIVERGENCE

    CONSTRAINT uq_contradiction UNIQUE (booth_id, entity, source_a, source_b, computed_at)
);

CREATE INDEX IF NOT EXISTS idx_contra_booth   ON contradiction_flags(booth_id, computed_at DESC);
CREATE INDEX IF NOT EXISTS idx_contra_entity  ON contradiction_flags(entity, delta DESC);

-- ── 4. SCHEME GAP TYPES ───────────────────────────────────────────────────────
-- Richer classification for each scheme-booth combination.

CREATE TABLE IF NOT EXISTS scheme_gap_analysis (
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    booth_id            VARCHAR(40)  NOT NULL,
    panchayat_id        VARCHAR(40),
    scheme_name         VARCHAR(200) NOT NULL,
    issue_tag           VARCHAR(50),
    computed_at         TIMESTAMPTZ  DEFAULT NOW(),

    -- Coverage & completion
    beneficiary_count   INTEGER      DEFAULT 0,
    coverage_pct        FLOAT,       -- beneficiaries / total_voters (if available)
    completion_status   VARCHAR(30), -- planned | in_progress | completed

    -- Sentiment
    negative_events     INTEGER      DEFAULT 0,
    positive_events     INTEGER      DEFAULT 0,
    total_events        INTEGER      DEFAULT 0,
    avg_sentiment       FLOAT        DEFAULT 0,

    -- Classification
    gap_type            VARCHAR(30),
    -- execution_gap    : completed + high beneficiaries + negative sentiment
    -- reach_gap        : completed + low beneficiaries + negative sentiment (not reaching people)
    -- awareness_gap    : completed + high beneficiaries + neutral sentiment (people don't know)
    -- performing_well  : completed + positive sentiment
    -- in_progress      : not completed yet
    -- no_data          : no sentiment events to judge

    gap_label           TEXT,        -- human-readable explanation
    priority            VARCHAR(10), -- HIGH | MEDIUM | LOW

    CONSTRAINT uq_scheme_gap UNIQUE (booth_id, scheme_name, computed_at)
);

CREATE INDEX IF NOT EXISTS idx_gap_booth  ON scheme_gap_analysis(booth_id, computed_at DESC);
CREATE INDEX IF NOT EXISTS idx_gap_type   ON scheme_gap_analysis(gap_type, priority);

-- ── 5. ADD COLUMNS TO booth_metrics ──────────────────────────────────────────

ALTER TABLE booth_metrics
    ADD COLUMN IF NOT EXISTS signal_consistency_score  FLOAT,
    ADD COLUMN IF NOT EXISTS has_contradiction          BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS dominant_narrative         VARCHAR(50),
    ADD COLUMN IF NOT EXISTS narrative_strength         FLOAT,
    ADD COLUMN IF NOT EXISTS quality_score              FLOAT,
    ADD COLUMN IF NOT EXISTS issue_momentum             JSONB;   -- if not already present
