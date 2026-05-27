"""
Alembic environment configuration.

Reads DATABASE_URL from environment (via python-dotenv) so credentials
never appear in source files.

Auto-generates migration scripts by comparing SQLAlchemy metadata
against the live database schema.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv

# ── Path setup ────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[3]  # project root
sys.path.insert(0, str(_ROOT))

load_dotenv(_ROOT / ".env")

# ── Alembic Config object ──────────────────────────────────────────────────────
config = context.config

# Set DB URL from environment (overrides alembic.ini placeholder)
db_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Configure logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import all table metadata for autogenerate ────────────────────────────────
# Import your SQLAlchemy Base here so Alembic can compare against DB schema.
try:
    from backend.db import Base as _Base  # noqa: F401

    target_metadata = _Base.metadata
except ImportError:
    # Graceful degradation if models not yet defined
    target_metadata = None  # type: ignore[assignment]


# ── Run migrations ─────────────────────────────────────────────────────────────


def run_migrations_offline() -> None:
    """Run migrations without a DB connection (generates SQL scripts)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    from sqlalchemy import engine_from_config, pool

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
