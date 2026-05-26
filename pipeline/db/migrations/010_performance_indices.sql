-- =============================================================================
-- Migration 010: Performance Indices
-- Optimise query speeds on JOIN paths and foreign keys (booth_id, channel_id, ac_id)
-- =============================================================================

-- 1. Index on turnout_stats(booth_id, election_year) for election results queries
CREATE INDEX IF NOT EXISTS idx_turnout_stats_booth_yr ON turnout_stats(booth_id, election_year);

-- 2. Index on booth_master(panchayat_hint) for panchayat mapping resolution
CREATE INDEX IF NOT EXISTS idx_booth_master_panchayat_hint ON booth_master(panchayat_hint) WHERE panchayat_hint IS NOT NULL;

-- 3. Index on yt_videos(channel_id) for channel mapping joins
CREATE INDEX IF NOT EXISTS idx_yt_videos_channel_id ON yt_videos(channel_id);

-- 4. Index on candidate_master(party) for party-specific candidate listings
CREATE INDEX IF NOT EXISTS idx_candidate_party ON candidate_master(party);

-- 5. Composite index on scheme_activity(panchayat_id, status) for scheme pipeline tracking
CREATE INDEX IF NOT EXISTS idx_scheme_activity_panchayat_status ON scheme_activity(panchayat_id, status);
