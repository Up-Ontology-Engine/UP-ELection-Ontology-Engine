"""Shared database connection helpers for FastAPI."""
import os
from contextlib import contextmanager
from neo4j import GraphDatabase
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

# ── PostgreSQL ────────────────────────────────────────────────────────────────
_pg_engine: sa.Engine | None = None

def get_pg_engine() -> sa.Engine:
    global _pg_engine
    if _pg_engine is None:
        _pg_engine = sa.create_engine(
            os.environ["POSTGRES_URL"],
            pool_size=int(os.environ.get("POSTGRES_POOL_SIZE", 5)),
            pool_pre_ping=True,
        )
    return _pg_engine

# ── Neo4j ─────────────────────────────────────────────────────────────────────
_neo4j_driver = None

def get_neo4j_driver():
    global _neo4j_driver
    if _neo4j_driver is None:
        _neo4j_driver = GraphDatabase.driver(
            os.environ["NEO4J_URI"],
            auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
        )
    return _neo4j_driver

@contextmanager
def get_neo4j_session():
    driver = get_neo4j_driver()
    with driver.session() as session:
        yield session
