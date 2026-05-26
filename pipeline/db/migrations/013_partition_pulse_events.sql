-- =============================================================================
-- Migration: Partition pulse_events by RANGE (created_at)
-- Description: Optimizes query speed on massive social signal feeds by splitting
--              data into yearly partitions.
-- =============================================================================

-- 1. Rename existing table
ALTER TABLE pulse_events RENAME TO pulse_events_old;

-- 2. Create the new partitioned table (same schema plus PARTITION BY)
CREATE TABLE pulse_events (
    id                  UUID         DEFAULT gen_random_uuid(),
    source_type         VARCHAR(30)  NOT NULL,
    source_id           VARCHAR(100) NOT NULL,
    text_raw            TEXT,
    text_normalized_hi  TEXT,
    language_detected   VARCHAR(10),
    translation_method  VARCHAR(30),
    extraction_method   VARCHAR(30),
    llm_output          JSONB,
    rule_output         JSONB,
    entity              VARCHAR(200),
    entity_type         VARCHAR(30),
    issue               VARCHAR(50),
    polarity            SMALLINT,
    confidence          FLOAT,
    evidence            TEXT,
    final_polarity      SMALLINT,
    final_issue         VARCHAR(50),
    final_confidence    FLOAT,
    location_text       VARCHAR(500),
    mapped_booth_id     VARCHAR(40),
    mapped_ac_id        VARCHAR(30),
    mapped_panchayat_id VARCHAR(40),
    geo_level           VARCHAR(20),
    geo_confidence      FLOAT,
    source_weight       FLOAT          DEFAULT 0.6,
    processing_errors   JSONB          DEFAULT '[]',
    created_at          TIMESTAMPTZ    DEFAULT NOW(),
    PRIMARY KEY (id, created_at)  -- Composite primary key required for partitioning
) PARTITION BY RANGE (created_at);

-- 3. Create partitions for years 2024, 2025, 2026, 2027 and a default partition
CREATE TABLE IF NOT EXISTS pulse_events_y2024 PARTITION OF pulse_events
    FOR VALUES FROM ('2024-01-01 00:00:00+00') TO ('2025-01-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS pulse_events_y2025 PARTITION OF pulse_events
    FOR VALUES FROM ('2025-01-01 00:00:00+00') TO ('2026-01-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS pulse_events_y2026 PARTITION OF pulse_events
    FOR VALUES FROM ('2026-01-01 00:00:00+00') TO ('2027-01-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS pulse_events_y2027 PARTITION OF pulse_events
    FOR VALUES FROM ('2027-01-01 00:00:00+00') TO ('2028-01-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS pulse_events_default PARTITION OF pulse_events DEFAULT;

-- 4. Copy existing data into the partitioned table
INSERT INTO pulse_events (
    id, source_type, source_id, text_raw, text_normalized_hi, language_detected,
    translation_method, extraction_method, llm_output, rule_output, entity,
    entity_type, issue, polarity, confidence, evidence, final_polarity,
    final_issue, final_confidence, location_text, mapped_booth_id, mapped_ac_id,
    mapped_panchayat_id, geo_level, geo_confidence, source_weight, processing_errors,
    created_at
)
SELECT 
    id, source_type, source_id, text_raw, text_normalized_hi, language_detected,
    translation_method, extraction_method, llm_output, rule_output, entity,
    entity_type, issue, polarity, confidence, evidence, final_polarity,
    final_issue, final_confidence, location_text, mapped_booth_id, mapped_ac_id,
    mapped_panchayat_id, geo_level, geo_confidence, source_weight, processing_errors,
    created_at
FROM pulse_events_old;

-- 5. Drop old table
DROP TABLE pulse_events_old CASCADE;

-- 6. Create indexes on the partitioned table (Postgres automatically propagates indexes to partitions)
CREATE INDEX IF NOT EXISTS idx_pulse_booth ON pulse_events(mapped_booth_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pulse_ac ON pulse_events(mapped_ac_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pulse_entity ON pulse_events(entity, entity_type);
CREATE INDEX IF NOT EXISTS idx_pulse_issue ON pulse_events(issue, final_polarity);
