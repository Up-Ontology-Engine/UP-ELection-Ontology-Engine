import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_input_validation_ac_id_safe():
    response = client.get("/ac/GKP_URBAN/booths")
    # Even if database is empty/not running, it should not fail with 400 (it should resolve or 404/500/200)
    assert response.status_code != 400

def test_input_validation_ac_id_forbidden_chars():
    # Test single quote
    response = client.get("/ac/GKP_URBAN'/booths")
    assert response.status_code == 400
    assert "Malformed" in response.json()["detail"]

    # Test semicolon
    response = client.get("/ac/GKP_URBAN;--/booths")
    assert response.status_code == 400
    assert "Malformed" in response.json()["detail"]

    # Test nested query parameters validation
    response = client.get("/graph/subgraph", params={"entity_type": "AC", "entity_id": "GKP'; DROP TABLE candidates;--"})
    assert response.status_code == 400
    assert "Malformed" in response.json()["detail"]

def test_pydantic_validation():
    # Test reasoning query length limit
    response = client.post("/reasoning/query", json={"question": "a" * 1005})
    assert response.status_code == 422

    # Test role Literal constraint in AddMessageRequest
    # session_id should fail with 404 if valid but not exists, but if we pass malformed role, it's 422
    response = client.post("/chat/sessions/sess123/messages", json={
        "role": "invalid_role",
        "content": "hello",
        "ts": "123"
    })
    assert response.status_code == 422

def test_health_check_details():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "postgres" in data
    assert "redis" in data
    assert "neo4j" in data
    assert "status" in data
    assert "ac" in data

def test_subgraph_parameters():
    # Make a valid subgraph query with pagination and rel_types filtering parameters
    response = client.get("/graph/subgraph", params={
        "entity_type": "AC",
        "entity_id": "GKP_URBAN",
        "limit": 10,
        "skip": 5,
        "rel_types": ["IN_AC", "HAS_ISSUE"]
    })
    # Since it might fall back to SQL if Neo4j is not connected/running,
    # it should still return a valid response structure: dict containing "nodes" and "edges"
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data

