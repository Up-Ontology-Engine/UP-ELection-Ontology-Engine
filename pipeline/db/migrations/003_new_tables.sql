-- =============================================================================
-- Migration 003: MLA Work, AC Demographics, Booth Aggregate Placeholder
-- Run: psql $POSTGRES_URL -f db/migrations/003_new_tables.sql
-- =============================================================================

-- ── 1. MLA WORK TABLE ────────────────────────────────────────────────────────
-- Tracks work done by MLAs: questions raised, bills, development projects, schemes

CREATE TABLE IF NOT EXISTS mla_work (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id    VARCHAR(40),
    ac_id           VARCHAR(30),
    work_type       VARCHAR(50),   -- questions | bills | development | scheme | attendance
    title           TEXT,
    description     TEXT,
    session_year    VARCHAR(10),
    work_date       DATE,
    source_url      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mla_work_candidate ON mla_work(candidate_id);
CREATE INDEX IF NOT EXISTS idx_mla_work_ac        ON mla_work(ac_id);
CREATE INDEX IF NOT EXISTS idx_mla_work_type      ON mla_work(work_type);

-- Add work summary columns to candidate_master
ALTER TABLE candidate_master
    ADD COLUMN IF NOT EXISTS questions_count  INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS bills_count      INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS attendance_pct   FLOAT   DEFAULT 0,
    ADD COLUMN IF NOT EXISTS dev_works_count  INTEGER DEFAULT 0;

-- ── 2. AC DEMOGRAPHICS TABLE ─────────────────────────────────────────────────
-- AC-level aggregated voter demographics (gender + age bands)
-- Sourced from NVSP / CEO UP (booth-level Part No was missing from local XLSX)

CREATE TABLE IF NOT EXISTS ac_demographics (
    ac_id           VARCHAR(30) PRIMARY KEY REFERENCES ac_master(ac_id),
    total_voters    INTEGER DEFAULT 0,
    male_voters     INTEGER DEFAULT 0,
    female_voters   INTEGER DEFAULT 0,
    other_voters    INTEGER DEFAULT 0,
    age_18_25       INTEGER DEFAULT 0,
    age_26_40       INTEGER DEFAULT 0,
    age_40_60       INTEGER DEFAULT 0,
    age_60_plus     INTEGER DEFAULT 0,
    data_source     VARCHAR(50),
    last_updated    TIMESTAMPTZ DEFAULT NOW(),
    notes           TEXT
);

-- ── 3. VIRTUAL BOOTHS FOR AC-LEVEL AGGREGATES ────────────────────────────────
-- booth_results FK requires booth_id in booth_master.
-- We insert one "TOTAL" placeholder per AC so ECI result scraper can load
-- AC-level vote totals without violating the constraint.
-- These are distinguishable by booth_number = 0.

INSERT INTO booth_master (booth_id, ac_id, booth_number, polling_station_name)
SELECT
    ac_id || '_TOTAL' AS booth_id,
    ac_id,
    0                  AS booth_number,
    'AC Total Aggregate' AS polling_station_name
FROM ac_master
ON CONFLICT (booth_id) DO NOTHING;

-- ── 4. TURNOUT_STATS: allow NULL total_voters ─────────────────────────────────
-- original schema has total_voters NOT NULL — relaxed so partial data loads work
ALTER TABLE turnout_stats
    ALTER COLUMN total_voters DROP NOT NULL;

-- ── 5. CANDIDATE AFFIDAVITS: add source_pdf column ───────────────────────────
-- (pdf_url already in 001_initial.sql; this adds any missing index)
CREATE INDEX IF NOT EXISTS idx_affidavits_candidate
    ON candidate_affidavits(candidate_id, election_year);
