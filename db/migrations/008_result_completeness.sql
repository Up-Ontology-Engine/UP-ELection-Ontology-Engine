-- =============================================================================
-- Migration 008: Result completeness tracking
--
-- Strategy: Additive and safe. Adds result_completeness_status to
-- candidate_party_history, backfills existing data to 'complete', and applies
-- check and NOT NULL constraints.
-- =============================================================================

-- 1. Add the column result_completeness_status as nullable temporarily for backfilling
ALTER TABLE candidate_party_history ADD COLUMN IF NOT EXISTS result_completeness_status VARCHAR(40);

-- 2. Backfill existing historical election results to 'complete'
UPDATE candidate_party_history
SET result_completeness_status = 'complete'
WHERE result_completeness_status IS NULL;

-- 3. Add CHECK constraint to enforce allowed enums
ALTER TABLE candidate_party_history ADD CONSTRAINT chk_result_completeness_status
    CHECK (result_completeness_status IN ('complete', 'winner_runnerup_only', 'partial', 'missing'));

-- 4. Enforce NOT NULL constraint now that everything is backfilled
ALTER TABLE candidate_party_history ALTER COLUMN result_completeness_status SET NOT NULL;

-- 5. Document semantic purpose
COMMENT ON COLUMN candidate_party_history.result_completeness_status IS
    'Dataset completeness level: complete (all candidates) | winner_runnerup_only (only top 2) | partial (some missing) | missing (no result votes)';
