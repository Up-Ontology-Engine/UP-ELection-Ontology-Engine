"""Shared database connection helpers for FastAPI."""
import os
from contextlib import contextmanager
from typing import Optional

from neo4j import GraphDatabase
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

# ── PostgreSQL ────────────────────────────────────────────────────────────────
_pg_engine: Optional[sa.Engine] = None

def get_pg_engine() -> sa.Engine:
    global _pg_engine
    if _pg_engine is None:
        pg_url = os.environ.get("POSTGRES_URL")
        if not pg_url:
            raise RuntimeError(
                "POSTGRES_URL environment variable is not set. Set POSTGRES_URL to your database URL."
            )
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
            raise RuntimeError(
                "NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD must be set in the environment."
            )
        try:
            _neo4j_driver = GraphDatabase.driver(uri, auth=(user, pwd))
        except Exception as e:
            raise RuntimeError(
                f"Failed to create Neo4j driver for {uri}: {e!s}"
            )
    return _neo4j_driver

@contextmanager
def get_neo4j_session():
    driver = get_neo4j_driver()
    with driver.session() as session:
        yield session
