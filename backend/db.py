"""Shared database connection helpers for FastAPI."""

import os
from contextlib import contextmanager
from typing import Optional

import sqlalchemy as sa
from neo4j import GraphDatabase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


# ── SQLAlchemy Base (for Alembic autogenerate) ────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── PostgreSQL ────────────────────────────────────────────────────────────────
_pg_engine: Optional[sa.Engine] = None


def get_pg_engine() -> sa.Engine:
    global _pg_engine
    if _pg_engine is None:
        pg_url = os.environ.get("POSTGRES_URL") or os.environ.get("DATABASE_URL")
        if not pg_url:
            raise RuntimeError("POSTGRES_URL environment variable is not set.")
        _pg_engine = sa.create_engine(
            pg_url,
            pool_size=int(os.environ.get("POSTGRES_POOL_SIZE", 5)),
            pool_pre_ping=True,
        )
    return _pg_engine


# ── Neo4j ─────────────────────────────────────────────────────────────────────
_neo4j_driver = None


def get_neo4j_driver():
    global _neo4j_driver
    if _neo4j_driver is None:
        uri = os.environ.get("NEO4J_URI")
        user = os.environ.get("NEO4J_USER")
        pwd = os.environ.get("NEO4J_PASSWORD")
        if not uri or not user or not pwd:
            raise RuntimeError("NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD must be set.")
        try:
            _neo4j_driver = GraphDatabase.driver(uri, auth=(user, pwd))
        except Exception as e:
            raise RuntimeError(f"Failed to create Neo4j driver for {uri}: {e!s}")
    return _neo4j_driver


@contextmanager
def get_neo4j_session():
    driver = get_neo4j_driver()
    with driver.session() as session:
        yield session


# ── Redis ─────────────────────────────────────────────────────────────────────
_redis_client = None  # module-level — tests patch this directly


def get_redis_client():
    """
    Return a Redis client, or None if REDIS_URL is not set / connection fails.
    Tests can patch api.db._redis_client directly.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        return None
    try:
        import redis as _redis

        client = _redis.from_url(redis_url, socket_connect_timeout=2, decode_responses=True)
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception:
        return None


# ── Asynchronous PostgreSQL (asyncpg) ─────────────────────────────────────────

_async_pg_engine = None
_async_session_maker = None


def get_async_pg_engine():
    """Get or create the async SQLAlchemy engine using asyncpg driver."""
    global _async_pg_engine
    if _async_pg_engine is None:
        pg_url = os.environ.get("POSTGRES_URL") or os.environ.get("DATABASE_URL")
        if not pg_url:
            raise RuntimeError("POSTGRES_URL or DATABASE_URL not set.")
        # Translate to asyncpg scheme
        if pg_url.startswith("postgresql://"):
            pg_url = pg_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif pg_url.startswith("postgres://"):
            pg_url = pg_url.replace("postgres://", "postgresql+asyncpg://", 1)

        # PgBouncer transaction pooling optimizations.
        # Prepared statement caching must be disabled for transaction pooling (port 6432 by default)
        # to avoid "prepared statement does not exist" errors as connections are multiplexed.
        connect_args = {}
        is_pgbouncer = ":6432" in pg_url
        disable_stmt_cache = os.environ.get("DISABLE_PREPARED_STATEMENTS", "true").lower() == "true"

        if is_pgbouncer or disable_stmt_cache:
            connect_args["prepared_statement_cache_size"] = 0

        _async_pg_engine = create_async_engine(
            pg_url,
            pool_size=int(os.environ.get("POSTGRES_POOL_SIZE", 10)),
            pool_pre_ping=True,
            connect_args=connect_args,
        )
    return _async_pg_engine


def get_async_sessionmaker():
    """Get the asynchronous session maker."""
    global _async_session_maker
    if _async_session_maker is None:
        engine = get_async_pg_engine()
        _async_session_maker = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_maker
