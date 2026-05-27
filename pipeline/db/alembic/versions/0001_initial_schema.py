# ruff: noqa: E402, F401, F404, F405, F841, F811
"""Alembic migration script template."""

revision: str = "0001"
down_revision = None
branch_labels = None
depends_on = None

from alembic import op


def upgrade() -> None:
    """Create initial schema — idempotent (IF NOT EXISTS)."""

    # ingestion_track — watermarks for incremental scraping
    op.execute("""
        CREATE TABLE IF NOT EXISTS ingestion_track (
            source_id           TEXT        PRIMARY KEY,
            last_article_at     TIMESTAMPTZ,
            last_ingested_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ingested_count      INTEGER     NOT NULL DEFAULT 0
        )
    """)

    # pulse_events — core NLP sentiment events from scrapers
    op.execute("""
        CREATE TABLE IF NOT EXISTS pulse_events (
            id                  BIGSERIAL   PRIMARY KEY,
            mapped_booth_id     TEXT,
            entity              TEXT,
            issue               TEXT,
            final_polarity      NUMERIC(4,3),
            confidence          NUMERIC(4,3),
            language            TEXT,
            election_year       INTEGER     DEFAULT 2022,
            source_url          TEXT,
            source_id           TEXT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_pulse_events_booth_created
        ON pulse_events (mapped_booth_id, created_at DESC)
    """)

    # booth_narratives — computed narrative aggregations
    op.execute("""
        CREATE TABLE IF NOT EXISTS booth_narratives (
            id              BIGSERIAL   PRIMARY KEY,
            booth_id        TEXT        NOT NULL,
            narrative_type  TEXT,
            strength        NUMERIC(5,4),
            description     TEXT,
            top_issues      JSONB,
            top_entities    JSONB,
            evidence_count  INTEGER,
            confidence      NUMERIC(5,4),
            election_year   INTEGER     DEFAULT 2022,
            computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            window_days     INTEGER     DEFAULT 7
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_booth_narratives_booth_computed
        ON booth_narratives (booth_id, computed_at DESC)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS booth_narratives CASCADE")
    op.execute("DROP TABLE IF EXISTS pulse_events CASCADE")
    op.execute("DROP TABLE IF EXISTS ingestion_track CASCADE")
