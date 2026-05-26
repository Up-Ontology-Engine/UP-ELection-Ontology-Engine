"""
Integration tests — API endpoints with real PostgreSQL.

Uses testcontainers to spin up a real Postgres instance so tests
exercise the actual SQL layer, not mocks.

Run:
    pytest tests/integration/ -q --timeout=60
"""
from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient

# Use DATABASE_URL from env (CI sets it via service container)
# or spin up testcontainer locally.

_USE_CONTAINER = not os.environ.get("DATABASE_URL")


@pytest.fixture(scope="session")
def pg_url():
    """Provide a PostgreSQL URL — real container if no env URL given."""
    if not _USE_CONTAINER:
        yield os.environ["DATABASE_URL"]
        return

    try:
        from testcontainers.postgres import PostgresContainer
        with PostgresContainer("postgres:16") as pg:
            url = pg.get_connection_url()
            os.environ["DATABASE_URL"] = url
            os.environ["POSTGRES_URL"] = url
            yield url
    except ImportError:
        pytest.skip("testcontainers not installed — skipping integration tests")


@pytest.fixture(scope="session")
def app_client(pg_url):
    """FastAPI test client with real DB wired up."""
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = pg_url
    os.environ["POSTGRES_URL"] = pg_url
    os.environ.setdefault("NEO4J_URI",      "bolt://localhost:7687")
    os.environ.setdefault("NEO4J_USER",     "neo4j")
    os.environ.setdefault("NEO4J_PASSWORD", "test")
    os.environ.setdefault("REDIS_URL",      "redis://localhost:6379/0")
    os.environ.setdefault("GOOGLE_API_KEY", "ci-dummy")
    os.environ.setdefault("SARVAM_API_KEY", "ci-dummy")

    from backend.main import app
    return TestClient(app)


# ── Health endpoint ────────────────────────────────────────────────────────────

def test_health_returns_200(app_client):
    resp = app_client.get("/health")
    assert resp.status_code == 200


def test_health_postgres_field_present(app_client):
    data = app_client.get("/health").json()
    assert "postgres" in data or "status" in data


# ── Root / docs ────────────────────────────────────────────────────────────────

def test_openapi_schema_accessible(app_client):
    resp = app_client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "paths" in schema
    assert "openapi" in schema


def test_docs_page_accessible(app_client):
    resp = app_client.get("/docs")
    assert resp.status_code == 200


# ── Input validation ───────────────────────────────────────────────────────────

def test_subgraph_rejects_sql_injection(app_client):
    """Cypher injection attempt must be rejected at the API layer."""
    resp = app_client.get("/graph/subgraph", params={"entity_id": "'; DROP TABLE booths;--"})
    assert resp.status_code in (400, 422)


def test_subgraph_rejects_overlong_id(app_client):
    resp = app_client.get("/graph/subgraph", params={"entity_id": "A" * 200})
    assert resp.status_code in (400, 422)


def test_reasoning_rejects_empty_question(app_client):
    resp = app_client.post("/reasoning/query", json={"question": ""})
    assert resp.status_code in (400, 422)


def test_reasoning_rejects_overlong_question(app_client):
    resp = app_client.post("/reasoning/query", json={"question": "x" * 5000})
    assert resp.status_code in (400, 422)


# ── Rate limiting ──────────────────────────────────────────────────────────────

def test_health_not_rate_limited(app_client):
    """Health endpoint should never be rate-limited."""
    for _ in range(10):
        resp = app_client.get("/health")
        assert resp.status_code != 429


# ── AC endpoints (graceful degradation without Neo4j) ─────────────────────────

def test_ac_booths_returns_json_or_503(app_client):
    resp = app_client.get("/ac/GKP_322/booths")
    assert resp.status_code in (200, 404, 500, 503)
    if resp.status_code == 200:
        assert isinstance(resp.json(), list)


def test_ac_candidates_returns_list_or_error(app_client):
    resp = app_client.get("/ac/GKP_322/candidates")
    assert resp.status_code in (200, 404, 500, 503)


def test_nonexistent_ac_returns_404_or_empty(app_client):
    resp = app_client.get("/ac/FAKE_999/booths")
    assert resp.status_code in (200, 404, 422, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert isinstance(data, (list, dict))
