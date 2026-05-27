import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Mock redis client
mock_redis = MagicMock()
mock_redis.get.return_value = None
mock_redis.keys.return_value = ["cache:test"]


@pytest.fixture(scope="module", autouse=True)
def mock_redis_globally():
    import backend.db

    old_redis = backend.db._redis_client
    backend.db._redis_client = mock_redis
    yield
    backend.db._redis_client = old_redis


from backend.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_env():
    os.environ["TEST_CACHE"] = "true"
    yield
    if "TEST_CACHE" in os.environ:
        del os.environ["TEST_CACHE"]


def test_cache_decorator_calls_redis():
    mock_redis.reset_mock()
    mock_redis.get.return_value = None

    # Mock return value of DB calls to avoid actual db hits
    with patch("backend.routers.booths.get_booths_for_ac", return_value=[{"booth_id": "1"}]):
        # First call: cache miss, should hit get and setex
        response1 = client.get("/ac/GKP_URBAN/booths")
        assert response1.status_code == 200
        mock_redis.get.assert_called_once()
        mock_redis.setex.assert_called_once()

        # Second call: cache hit, mock returns cached value
        mock_redis.reset_mock()
        mock_redis.get.return_value = '[{"booth_id": "1"}]'
        response2 = client.get("/ac/GKP_URBAN/booths")
        assert response2.status_code == 200
        mock_redis.get.assert_called_once()
        mock_redis.setex.assert_not_called()


def test_cache_invalidation_on_data_mutation():
    mock_redis.reset_mock()
    mock_redis.keys.return_value = ["cache:test"]

    with patch("backend.routers.booths.mark_beneficiary_contacted", return_value=True):
        response = client.patch(
            "/beneficiaries/123/contact", json={"notes": "Called", "worker_id": "W1"}
        )
        assert response.status_code == 200
        # Should clear cache by fetching keys and deleting them
        mock_redis.keys.assert_called_with("cache:*")
        mock_redis.delete.assert_called_once()


def test_reasoning_endpoint_rate_limit():
    from backend.main import limiter

    assert limiter is not None
