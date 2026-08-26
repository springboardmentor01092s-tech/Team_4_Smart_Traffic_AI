"""
tests/test_health/test_health_router.py

Unit and integration tests for production health, liveness, and readiness endpoints.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock

from app.core.database import get_db
from app.main import app


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    """GET /api/v1/health returns 200 with service metadata."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_liveness_check(client: AsyncClient) -> None:
    """GET /api/v1/health/live returns 200 alive state."""
    response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_readiness_check_success(client: AsyncClient) -> None:
    """GET /api/v1/health/ready returns 200 when database is accessible."""
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"
    assert "service" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_readiness_check_database_failure(client: AsyncClient) -> None:
    """GET /api/v1/health/ready returns 503 when database query fails."""
    async def failing_db():
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute.side_effect = Exception("Database connection lost")
        yield mock_session

    app.dependency_overrides[get_db] = failing_db
    try:
        response = await client.get("/api/v1/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unready"
        assert data["database"] == "disconnected"
    finally:
        # restore client dependency override
        app.dependency_overrides.pop(get_db, None)
