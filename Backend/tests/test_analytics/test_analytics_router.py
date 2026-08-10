"""
tests/test_analytics/test_analytics_router.py
"""
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_get_summary(client: AsyncClient) -> None:
    # Public route, no token needed
    response = await client.get("/api/v1/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_segments" in data


async def test_get_congestion_heatmap(client: AsyncClient) -> None:
    response = await client.get("/api/v1/analytics/congestion-heatmap")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.skip(reason="date_trunc not supported in SQLite test db")
async def test_get_peak_hours(client: AsyncClient) -> None:
    response = await client.get("/api/v1/analytics/peak-hours")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_get_segment_history(client: AsyncClient) -> None:
    segment_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/analytics/segments/{segment_id}/history")
    # Should be 404 since segment doesn't exist
    assert response.status_code == 404


async def test_get_segment_trends_unauthorized(client: AsyncClient) -> None:
    segment_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/analytics/segments/{segment_id}/trends")
    # Missing token -> 403 (established behavior)
    assert response.status_code == 403


@pytest.mark.skip(reason="date_trunc not supported in SQLite test db")
async def test_get_segment_trends(client: AsyncClient, admin_token: str) -> None:
    segment_id = str(uuid.uuid4())
    response = await client.get(
        f"/api/v1/analytics/segments/{segment_id}/trends",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


@pytest.mark.skip(reason="date_trunc not supported in SQLite test db")
async def test_get_full_report(client: AsyncClient, admin_token: str) -> None:
    now = datetime.now(UTC)
    from_dt = (now - timedelta(days=1)).isoformat()
    to_dt = now.isoformat()

    response = await client.get(
        f"/api/v1/analytics/reports?from_dt={from_dt}&to_dt={to_dt}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert "active_segment_count" in response.json()


@pytest.mark.skip(reason="date_trunc not supported in SQLite test db")
async def test_get_full_report_invalid_dates(client: AsyncClient, admin_token: str) -> None:
    now = datetime.now(UTC)
    from_dt = now.isoformat()
    to_dt = (now - timedelta(days=1)).isoformat()

    response = await client.get(
        f"/api/v1/analytics/reports?from_dt={from_dt}&to_dt={to_dt}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Invalid date range
    assert response.status_code == 422
    assert response.json()["error_code"] == "INVALID_DATE_RANGE"
