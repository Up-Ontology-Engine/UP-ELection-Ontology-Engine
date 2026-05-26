-- =============================================================================
-- Migration 009: Voter segments + Conversion opportunity tables
-- =============================================================================

-- ── 1. Booth demographic segments (aggregated, no PII) ────────────────────────
-- One row per booth per segment type. Derived from electoral roll part files.
-- Age group and gender counts only — no names, voter IDs, or house numbers.

CREATE TABLE IF NOT EXISTS booth_demographic_segments (
    booth_id        VARCHAR(40)  NOT NULL,
    segment_type    VARCHAR(30)  NOT NULL,
    -- youth        : age 18-30
    -- first_voter  : age 18-21
    -- women        : gender = Female
    -- elderly      : age > 60
    -- working_age  : age 25-55
    count           INTEGER      NOT NULL DEFAULT 0,
    pct_of_voters   FLOAT,          -- count / total_voters from booth_master
    computed_at     TIMESTAMPTZ  DEFAULT NOW(),
    PRIMARY KEY (booth_id, segment_type)
);

CREATE INDEX IF NOT EXISTS idx_seg_type ON booth_demographic_segments(segment_type);

-- ── 2. Conversion opportunity scores ──────────────────────────────────────────
-- One row per booth. Derived from booth_results + booth_metrics +
-- scheme_gap_analysis + turnout_stats. Recomputed on each analytics run.

CREATE TABLE IF NOT EXISTS conversion_opportunity (
    booth_id                    VARCHAR(40)  PRIMARY KEY,
    persuasion_room_score       FLOAT,   -- 0-1: swing potential from margin + pulse divergence
    beneficiary_density_score   FLOAT,   -- 0-1: scheme beneficiaries / total voters
    turnout_mobilization_score  FLOAT,   -- 0-1: supportive + low historical turnout
    service_risk_score          FLOAT,   -- 0-1: execution gaps weighting negative sentiment
    overall_conversion_score    FLOAT,   -- 0-1: composite
    recommended_action          VARCHAR(30),
    -- awareness        : high beneficiaries + awareness_gap detected
    -- grievance_redress: high service_risk
    -- mobilization     : low turnout + supportive lean
    -- consolidation    : thin margin + persuasion room
    -- maintain         : stronghold, low risk
    action_reason               TEXT,
    computed_at                 TIMESTAMPTZ  DEFAULT NOW()
);
