-- =============================================================================
-- Migration 004: Schema fixes — candidate affidavits unique key, YouTube extras
-- Run: psql $POSTGRES_URL -f db/migrations/004_fixes.sql
-- =============================================================================

-- ── 1. CANDIDATE AFFIDAVITS: unique per candidate ─────────────────────────────
-- The seed / scraper uses ON CONFLICT (candidate_id), which requires a unique index.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_affidavit_candidate'
    ) THEN
        ALTER TABLE candidate_affidavits
            ADD CONSTRAINT uq_affidavit_candidate UNIQUE (candidate_id);
    END IF;
END $$;

-- ── 2. YT_VIDEOS: add content_hash + query_source columns ────────────────────
ALTER TABLE yt_videos
    ADD COLUMN IF NOT EXISTS content_hash  VARCHAR(64),
    ADD COLUMN IF NOT EXISTS query_source  TEXT,
    ADD COLUMN IF NOT EXISTS duration_secs FLOAT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_yt_videos_hash ON yt_videos(content_hash)
    WHERE content_hash IS NOT NULL;

-- ── 3. YT_COMMENTS: make video_id FK deferrable (comments may arrive before video) ─
-- Drop the original FK and re-add as deferrable so bulk inserts don't require
-- video rows to exist in the same transaction.
ALTER TABLE yt_comments
    DROP CONSTRAINT IF EXISTS yt_comments_video_id_fkey;

ALTER TABLE yt_comments
    ADD CONSTRAINT yt_comments_video_id_fkey
    FOREIGN KEY (video_id)
    REFERENCES yt_videos(video_id)
    ON DELETE SET NULL
    DEFERRABLE INITIALLY DEFERRED;

-- ── 4. PULSE_EVENTS_RAW: add video_id tracking ────────────────────────────────
ALTER TABLE pulse_events_raw
    ADD COLUMN IF NOT EXISTS video_id TEXT;
