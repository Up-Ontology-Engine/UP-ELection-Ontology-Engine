-- =============================================================================
-- Gorakhpur KG — Initial Schema
-- Run: psql $POSTGRES_URL -f db/migrations/001_initial.sql
-- =============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- fuzzy text search

-- =============================================================================
-- STRUCTURAL MASTER TABLES
-- =============================================================================

CREATE TABLE IF NOT EXISTS ac_master (
    ac_id           VARCHAR(30)  PRIMARY KEY,
    ac_name         VARCHAR(100) NOT NULL,
    ac_type         VARCHAR(20)  DEFAULT 'urban',  -- urban | rural
    district_id     VARCHAR(20)  DEFAULT 'GKP',
    district_name   VARCHAR(50)  DEFAULT 'Gorakhpur',
    state           VARCHAR(50)  DEFAULT 'Uttar Pradesh',
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS booth_master (
    booth_id                VARCHAR(40)  PRIMARY KEY,
    ac_id                   VARCHAR(30)  REFERENCES ac_master(ac_id),
    booth_number            INTEGER,
    polling_station_name    TEXT,
    address                 TEXT,
    locality_hint           VARCHAR(200),
    ward_name               VARCHAR(100),
    panchayat_hint          VARCHAR(100),
    lat                     DECIMAL(10,7),
    lon                     DECIMAL(10,7),
    male_voters             INTEGER      DEFAULT 0,
    female_voters           INTEGER      DEFAULT 0,
    other_voters            INTEGER      DEFAULT 0,
    total_voters            INTEGER      DEFAULT 0,
    blo_name                VARCHAR(200),
    blo_contact             VARCHAR(20),
    created_at              TIMESTAMPTZ  DEFAULT NOW(),
    updated_at              TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_booth_ac ON booth_master(ac_id);
CREATE INDEX IF NOT EXISTS idx_booth_locality ON booth_master USING gin(locality_hint gin_trgm_ops);

CREATE TABLE IF NOT EXISTS panchayat_master (
    panchayat_id    VARCHAR(40)  PRIMARY KEY,
    gp_name         VARCHAR(200) NOT NULL,
    block_name      VARCHAR(100),
    district_id     VARCHAR(20)  DEFAULT 'GKP',
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS booth_panchayat_mapping (
    booth_id        VARCHAR(40)  REFERENCES booth_master(booth_id),
    panchayat_id    VARCHAR(40)  REFERENCES panchayat_master(panchayat_id),
    match_score     FLOAT,
    match_method    VARCHAR(30),  -- fuzzy | manual | exact
    PRIMARY KEY (booth_id, panchayat_id)
);

-- =============================================================================
-- CANDIDATES & ELECTIONS
-- =============================================================================

CREATE TABLE IF NOT EXISTS candidate_master (
    candidate_id    VARCHAR(40)  PRIMARY KEY DEFAULT gen_random_uuid()::VARCHAR,
    name            VARCHAR(200) NOT NULL,
    name_hi         VARCHAR(200),
    party           VARCHAR(100) NOT NULL,
    ac_id           VARCHAR(30)  REFERENCES ac_master(ac_id),
    election_year   INTEGER      NOT NULL,
    is_incumbent    BOOLEAN      DEFAULT FALSE,
    is_primary_opp  BOOLEAN      DEFAULT FALSE,
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_candidate_ac ON candidate_master(ac_id, election_year);

CREATE TABLE IF NOT EXISTS candidate_affidavits (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id    VARCHAR(40)  REFERENCES candidate_master(candidate_id),
    election_year   INTEGER,
    criminal_cases  INTEGER      DEFAULT 0,
    serious_cases   INTEGER      DEFAULT 0,
    total_assets    BIGINT,
    total_liabilities BIGINT,
    education       VARCHAR(200),
    profession      VARCHAR(200),
    age             INTEGER,
    pdf_url         TEXT,
    raw_json        JSONB,
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);

-- =============================================================================
-- HISTORICAL ELECTION RESULTS
-- =============================================================================

CREATE TABLE IF NOT EXISTS booth_results (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    booth_id        VARCHAR(40)  REFERENCES booth_master(booth_id),
    election_year   INTEGER      NOT NULL,
    party           VARCHAR(100),
    candidate_id    VARCHAR(40),
    votes           INTEGER,
    vote_share      FLOAT,
    winner_flag     BOOLEAN      DEFAULT FALSE,
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_results_booth ON booth_results(booth_id, election_year);

CREATE TABLE IF NOT EXISTS turnout_stats (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    booth_id        VARCHAR(40)  REFERENCES booth_master(booth_id),
    election_year   INTEGER      NOT NULL,
    total_voters    INTEGER,
    total_votes     INTEGER,
    turnout_percent FLOAT,
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);

-- =============================================================================
-- SCHEMES & GOVERNANCE
-- =============================================================================

CREATE TABLE IF NOT EXISTS scheme_activity (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    panchayat_id    VARCHAR(40)  REFERENCES panchayat_master(panchayat_id),
    scheme_name     VARCHAR(200) NOT NULL,
    issue_tag       VARCHAR(50),   -- water | roads | housing | electricity | jobs
    activity_desc   TEXT,
    beneficiary_count INTEGER,
    status          VARCHAR(30),   -- planned | in_progress | completed
    financial_year  VARCHAR(10),
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scheme_panchayat ON scheme_activity(panchayat_id);
CREATE INDEX IF NOT EXISTS idx_scheme_issue ON scheme_activity(issue_tag);

-- =============================================================================
-- DIGITAL SIGNAL INGESTION
-- =============================================================================

CREATE TABLE IF NOT EXISTS yt_channels (
    channel_id      VARCHAR(100) PRIMARY KEY,
    channel_name    VARCHAR(200),
    subscriber_count INTEGER,
    relevance_tag   VARCHAR(50),
    added_at        TIMESTAMPTZ  DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS yt_videos (
    video_id        VARCHAR(50)  PRIMARY KEY,
    channel_id      VARCHAR(100) REFERENCES yt_channels(channel_id),
    title           TEXT,
    description     TEXT,
    published_at    TIMESTAMPTZ,
    view_count      INTEGER,
    like_count      INTEGER,
    comment_count   INTEGER,
    url             TEXT,
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS yt_comments (
    comment_id      VARCHAR(100) PRIMARY KEY,
    video_id        VARCHAR(50)  REFERENCES yt_videos(video_id),
    author          VARCHAR(200),
    text_raw        TEXT         NOT NULL,
    like_count      INTEGER      DEFAULT 0,
    published_at    TIMESTAMPTZ,
    parent_id       VARCHAR(100),
    content_hash    VARCHAR(64),   -- sha256 for dedup
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_yt_comments_video ON yt_comments(video_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_yt_comments_hash ON yt_comments(content_hash);

CREATE TABLE IF NOT EXISTS news_articles (
    article_id      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    source          VARCHAR(50)  NOT NULL,   -- jagran | amarujala | nbt | local
    headline        TEXT,
    body_raw        TEXT,
    url             TEXT         UNIQUE,
    published_at    TIMESTAMPTZ,
    district_hint   VARCHAR(100),
    ac_hint         VARCHAR(100),
    content_hash    VARCHAR(64),
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_news_source ON news_articles(source, published_at DESC);

-- =============================================================================
-- NLP PIPELINE TABLES
-- =============================================================================

CREATE TABLE IF NOT EXISTS pulse_events_raw (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type     VARCHAR(30)  NOT NULL,   -- youtube | news | survey | field_note
    source_id       VARCHAR(100) NOT NULL,
    text_raw        TEXT         NOT NULL,
    created_at      TIMESTAMPTZ  DEFAULT NOW(),
    processed       BOOLEAN      DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_pulse_raw_unprocessed ON pulse_events_raw(processed, created_at);

CREATE TABLE IF NOT EXISTS pulse_events (
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type         VARCHAR(30)  NOT NULL,
    source_id           VARCHAR(100) NOT NULL,
    text_raw            TEXT,
    text_normalized_hi  TEXT,
    language_detected   VARCHAR(10),
    translation_method  VARCHAR(30),   -- bhashini | indictrans2 | none
    -- LLM extraction
    extraction_method   VARCHAR(30),   -- llm | rule_based | llm+rule_fallback
    llm_output          JSONB,
    rule_output         JSONB,
    -- Final resolved values
    entity              VARCHAR(200),
    entity_type         VARCHAR(30),
    issue               VARCHAR(50),
    polarity            SMALLINT,      -- -1 | 0 | 1
    confidence          FLOAT,
    evidence            TEXT,
    final_polarity      SMALLINT,
    final_issue         VARCHAR(50),
    final_confidence    FLOAT,
    -- Geo resolution
    location_text       VARCHAR(500),
    mapped_booth_id     VARCHAR(40),
    mapped_ac_id        VARCHAR(30),
    mapped_panchayat_id VARCHAR(40),
    geo_level           VARCHAR(20),   -- booth | panchayat | ac | district
    geo_confidence      FLOAT,
    -- Weighting
    source_weight       FLOAT          DEFAULT 0.6,  -- youtube=0.6, news=0.4, survey=1.0
    -- Audit
    processing_errors   JSONB          DEFAULT '[]',
    created_at          TIMESTAMPTZ    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pulse_booth ON pulse_events(mapped_booth_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pulse_ac ON pulse_events(mapped_ac_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pulse_entity ON pulse_events(entity, entity_type);
CREATE INDEX IF NOT EXISTS idx_pulse_issue ON pulse_events(issue, final_polarity);

-- =============================================================================
-- AGGREGATED METRICS
-- =============================================================================

CREATE TABLE IF NOT EXISTS booth_metrics (
    booth_id            VARCHAR(40)  NOT NULL,
    window_start        TIMESTAMPTZ  NOT NULL,
    window_end          TIMESTAMPTZ  NOT NULL,
    bjp_pulse_score     FLOAT,
    opp_pulse_score     FLOAT,
    digital_lean        FLOAT,        -- bjp - opp
    digital_lean_label  VARCHAR(20),  -- "Lean BJP" | "Lean Opp" | "Neutral" | "Contested"
    top_issue           VARCHAR(50),
    issue_breakdown     JSONB,         -- {water: 0.3, jobs: 0.2, ...}
    issue_momentum      JSONB,         -- {water: +0.22, jobs: +0.10, ...}
    scheme_gap_issues   JSONB,         -- issues where scheme exists but sentiment negative
    event_count         INTEGER,
    data_confidence     FLOAT,
    confidence_label    VARCHAR(20),   -- "HIGH" | "MEDIUM" | "LOW" | "INSUFFICIENT"
    last_computed_at    TIMESTAMPTZ    DEFAULT NOW(),
    PRIMARY KEY (booth_id, window_start)
);

CREATE TABLE IF NOT EXISTS ac_metrics (
    ac_id               VARCHAR(30)  NOT NULL,
    window_start        TIMESTAMPTZ  NOT NULL,
    bjp_pulse_score     FLOAT,
    opp_pulse_score     FLOAT,
    digital_lean        FLOAT,
    top_issues          JSONB,
    booth_coverage      INTEGER,      -- how many booths have data
    total_booths        INTEGER,
    event_count         INTEGER,
    last_computed_at    TIMESTAMPTZ  DEFAULT NOW(),
    PRIMARY KEY (ac_id, window_start)
);

-- =============================================================================
-- ISSUES REFERENCE TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS issues (
    issue_code      VARCHAR(30)  PRIMARY KEY,
    issue_name_en   VARCHAR(100),
    issue_name_hi   VARCHAR(200),
    category        VARCHAR(50),   -- infrastructure | economy | social | governance
    icon            VARCHAR(10)
);
