"""Smoke test for the /health endpoint."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def _mock_settings():
    """Provide minimal settings so the app can start without real env vars."""
    fake = {
        "AI_BASE_URL": "https://test.example.com/v1",
        "AI_API_KEY": "test-key",
        "AI_MODEL": "test-model",
        "REDIS_URL": "redis://localhost:6379/0",
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "ELASTICSEARCH_URL": "http://localhost:9200",
    }
    with patch("app.config.Settings", return_value=type("S", (), fake)()):
        with patch("app.main.settings", type("S", (), fake)()):
            with patch("app.main.aioredis") as mock_redis:
                mock_conn = AsyncMock()
                mock_redis.from_url.return_value = mock_conn
                yield


@pytest.mark.asyncio
async def test_health_returns_ok(_mock_settings):
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"
