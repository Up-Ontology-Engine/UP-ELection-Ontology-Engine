-- =============================================================================
-- Migration 007: Candidate enrichment — affidavit detail, expense, result facts
--
-- Strategy: additive only — no drops, no renames, no type changes.
-- Adds columns to candidate_master, candidate_affidavits, candidate_party_history
-- and creates the new candidate_expense_detail table.
-- Safe to re-run (all ALTER TABLE use IF NOT EXISTS, CREATE TABLE uses IF NOT EXISTS).
-- =============================================================================

-- ── 1. candidate_master — source identity + profession + voter enrollment ─────

ALTER TABLE candidate_master ADD COLUMN IF NOT EXISTS source_candidate_id  VARCHAR(40);
ALTER TABLE candidate_master ADD COLUMN IF NOT EXISTS source_system        VARCHAR(40)  DEFAULT 'myneta';
ALTER TABLE candidate_master ADD COLUMN IF NOT EXISTS election_slug        VARCHAR(80);
ALTER TABLE candidate_master ADD COLUMN IF NOT EXISTS display_name         VARCHAR(200);
ALTER TABLE candidate_master ADD COLUMN IF NOT EXISTS self_profession      VARCHAR(200);
ALTER TABLE candidate_master ADD COLUMN IF NOT EXISTS spouse_name          VARCHAR(200);
ALTER TABLE candidate_master ADD COLUMN IF NOT EXISTS spouse_profession    VARCHAR(200);
ALTER TABLE candidate_master ADD COLUMN IF NOT EXISTS voter_enrolled_ac_name VARCHAR(200);
ALTER TABLE candidate_master ADD COLUMN IF NOT EXISTS net_worth_rs         BIGINT;

COMMENT ON COLUMN candidate_master.source_candidate_id IS
    'Platform-native candidate ID (e.g. MyNeta candidate_id=3801)';
COMMENT ON COLUMN candidate_master.net_worth_rs IS
    'Computed: total_assets - total_liabilities from candidate_affidavits';


-- ── 2. candidate_affidavits — itemised asset / liability / case detail ────────

ALTER TABLE candidate_affidavits ADD COLUMN IF NOT EXISTS movable_assets_rs          BIGINT;
ALTER TABLE candidate_affidavits ADD COLUMN IF NOT EXISTS immovable_assets_rs        BIGINT;
ALTER TABLE candidate_affidavits ADD COLUMN IF NOT EXISTS movable_assets_json        JSONB;
ALTER TABLE candidate_affidavits ADD COLUMN IF NOT EXISTS immovable_assets_json      JSONB;
ALTER TABLE candidate_affidavits ADD COLUMN IF NOT EXISTS liabilities_json           JSONB;
ALTER TABLE candidate_affidavits ADD COLUMN IF NOT EXISTS criminal_case_details_json JSONB;
ALTER TABLE candidate_affidavits ADD COLUMN IF NOT EXISTS itr_income_json            JSONB;
ALTER TABLE candidate_affidavits ADD COLUMN IF NOT EXISTS source_affidavit_url       TEXT;
ALTER TABLE candidate_affidavits ADD COLUMN IF NOT EXISTS parse_status               VARCHAR(20) DEFAULT 'pending';
ALTER TABLE candidate_affidavits ADD COLUMN IF NOT EXISTS parse_error                TEXT;
ALTER TABLE candidate_affidavits ADD COLUMN IF NOT EXISTS html_snapshot_path         TEXT;
ALTER TABLE candidate_affidavits ADD COLUMN IF NOT EXISTS scraped_at                 TIMESTAMPTZ;

COMMENT ON COLUMN candidate_affidavits.parse_status IS
    'pending | scraped | partial | failed';
COMMENT ON COLUMN candidate_affidavits.movable_assets_json IS
    'Itemised movable assets as scraped: [{item, value_rs}]';
COMMENT ON COLUMN candidate_affidavits.itr_income_json IS
    'ITR income disclosures: [{year, total_income_rs}]';


-- ── 3. candidate_party_history — result fact enrichment ───────────────────────
--
-- This table (created in 006) already has: candidate_id, party_id, election_year,
-- constituency, votes_received, vote_share, result (won|lost|withdrew), margin.
-- We document its semantic role and add result-analysis columns.

COMMENT ON TABLE candidate_party_history IS
    'Candidate-election-result fact table (one row per candidate per election per constituency). '
    'Named candidate_party_history for historical reasons; functions as candidate_election_result_fact.';

ALTER TABLE candidate_party_history ADD COLUMN IF NOT EXISTS rank                  INTEGER;
ALTER TABLE candidate_party_history ADD COLUMN IF NOT EXISTS is_winner             BOOLEAN   DEFAULT FALSE;
ALTER TABLE candidate_party_history ADD COLUMN IF NOT EXISTS result_position_label VARCHAR(20);
ALTER TABLE candidate_party_history ADD COLUMN IF NOT EXISTS vote_gap_vs_winner    INTEGER;
ALTER TABLE candidate_party_history ADD COLUMN IF NOT EXISTS victory_margin_votes  INTEGER;
ALTER TABLE candidate_party_history ADD COLUMN IF NOT EXISTS valid_votes_total     INTEGER;
ALTER TABLE candidate_party_history ADD COLUMN IF NOT EXISTS results_source        VARCHAR(40) DEFAULT 'form20';
ALTER TABLE candidate_party_history ADD COLUMN IF NOT EXISTS source_results_url    TEXT;

COMMENT ON COLUMN candidate_party_history.result_position_label IS
    'winner | runner_up | other — pre-computed label for dashboard display';
COMMENT ON COLUMN candidate_party_history.vote_gap_vs_winner IS
    'winner_votes - this_candidate_votes; NULL for winner row';
COMMENT ON COLUMN candidate_party_history.victory_margin_votes IS
    'winner_votes - runner_up_votes; only populated on the winner row';
COMMENT ON COLUMN candidate_party_history.results_source IS
    'Data provenance: form20 | eci | indiavotes | manual';


-- ── 4. candidate_expense_detail — campaign expenditure (optional, non-blocking) ─

CREATE TABLE IF NOT EXISTS candidate_expense_detail (
    id                        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id              VARCHAR(40) NOT NULL REFERENCES candidate_master(candidate_id),
    election_year             INTEGER     NOT NULL,
    total_election_expense_rs BIGINT,
    own_funds_rs              BIGINT,
    party_funds_rs            BIGINT,
    external_funds_rs         BIGINT,
    expense_breakdown_json    JSONB,
    expense_data_quality      VARCHAR(40),
    expense_scrape_status     VARCHAR(20) DEFAULT 'pending',
    expense_scraped_at        TIMESTAMPTZ,
    source_expense_url        TEXT,
    parse_error               TEXT,
    created_at                TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (candidate_id, election_year)
);

COMMENT ON TABLE candidate_expense_detail IS
    'Campaign expenditure from MyNeta expense affidavit pages. Optional: pipeline '
    'continues if expense page is unavailable. Check expense_scrape_status.';
COMMENT ON COLUMN candidate_expense_detail.expense_scrape_status IS
    'pending | scraped | not_available | failed';

CREATE INDEX IF NOT EXISTS idx_expense_candidate
    ON candidate_expense_detail (candidate_id, election_year);
