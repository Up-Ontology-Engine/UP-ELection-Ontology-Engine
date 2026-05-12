-- =============================================================================
-- Migration 006: Intelligence layer tables
-- - entity_canonical: resolved entity identity store
-- - candidate_party_history: temporal party membership record
-- =============================================================================

-- ── 1. Entity canonical resolution table ──────────────────────────────────────
-- Stores every raw entity mention resolved by the NLP pipeline,
-- so dashboards can link free-text mentions back to graph nodes.
CREATE TABLE IF NOT EXISTS entity_canonical (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_text        TEXT        NOT NULL,
    canonical_id    TEXT,                        -- candidate_id | party_id | scheme name
    canonical_name  TEXT        NOT NULL,
    entity_type     VARCHAR(20) NOT NULL,         -- candidate | party | scheme | issue
    confidence      FLOAT       DEFAULT 0.0,
    source          VARCHAR(30) DEFAULT 'nlp',    -- nlp | manual | fuzzy
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_entity_canonical_raw
    ON entity_canonical (LOWER(raw_text), entity_type);
CREATE INDEX  IF NOT EXISTS idx_entity_canonical_id
    ON entity_canonical (canonical_id);

-- ── 2. Candidate party history (temporal intelligence) ─────────────────────────
-- Records each candidate's party affiliation per election cycle,
-- enabling party-switch detection and dynastic cluster analysis.
CREATE TABLE IF NOT EXISTS candidate_party_history (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id    TEXT        NOT NULL,
    candidate_name  TEXT,
    party_id        TEXT        NOT NULL,
    election_year   INTEGER     NOT NULL,
    constituency    TEXT,
    votes_received  INTEGER,
    vote_share      FLOAT,
    result          VARCHAR(10),                  -- won | lost | withdrew
    margin          INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (candidate_id, election_year, constituency)
);

CREATE INDEX IF NOT EXISTS idx_cph_candidate ON candidate_party_history(candidate_id);
CREATE INDEX IF NOT EXISTS idx_cph_party     ON candidate_party_history(party_id, election_year);
CREATE INDEX IF NOT EXISTS idx_cph_year      ON candidate_party_history(election_year);

-- ── 3. Populate candidate_party_history from existing candidate_master ----------
-- Seeds temporal records from the current election snapshot so the
-- party history graph is populated without manual data entry.
INSERT INTO candidate_party_history
    (candidate_id, candidate_name, party_id, election_year, constituency, result)
SELECT
    cm.candidate_id::text,
    cm.name,
    cm.party,
    COALESCE(cm.election_year, 2022),
    am.ac_name,
    CASE WHEN br.winner_candidate_id = cm.candidate_id::text THEN 'won' ELSE 'lost' END
FROM candidate_master cm
LEFT JOIN ac_master am ON cm.ac_id = am.ac_id
LEFT JOIN LATERAL (
    SELECT winner_candidate_id FROM booth_results
    WHERE ac_id = cm.ac_id AND election_year = COALESCE(cm.election_year, 2022)
    LIMIT 1
) br ON TRUE
WHERE cm.party IS NOT NULL
ON CONFLICT DO NOTHING;
