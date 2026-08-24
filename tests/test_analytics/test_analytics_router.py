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


async def test_get_congestion_heatmap(client: AsyncClient, test_db) -> None:
    # 1. Create a segment
    from app.models.segment import TrafficSegment
    from app.models.reading import TrafficReading, CongestionLevel
    import uuid
    from datetime import datetime, UTC
    
    seg_id = uuid.uuid4()
    segment = TrafficSegment(
        id=seg_id,
        name="Heatmap Test Segment",
        start_point="Point A",
        end_point="Point B",
        start_latitude=10.0,
        start_longitude=20.0,
        end_latitude=30.0,
        end_longitude=40.0,
        length_km=5.0,
        speed_limit_kmh=60,
    )
    test_db.add(segment)
    
    # 2. Create a reading for it
    reading = TrafficReading(
        segment_id=seg_id,
        vehicle_count=100,
        average_speed_kmh=50.0,
        congestion_level=CongestionLevel.MODERATE,
        recorded_at=datetime.now(UTC),
    )
    test_db.add(reading)
    await test_db.commit()

    # 3. Hit the endpoint
    response = await client.get("/api/v1/analytics/congestion-heatmap")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # Find our specific segment
    heatmap_item = next((item for item in data if item["segment_id"] == str(seg_id)), None)
    assert heatmap_item is not None
    
    # Verify geographic fields are present and correct
    assert heatmap_item["start_latitude"] == 10.0
    assert heatmap_item["start_longitude"] == 20.0
    assert heatmap_item["end_latitude"] == 30.0
    assert heatmap_item["end_longitude"] == 40.0
    
    # Verify reading fields
    assert heatmap_item["vehicle_count"] == 100
    assert heatmap_item["congestion_level"] == "MODERATE"


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


async def test_get_segment_trends_mocked(client: AsyncClient, admin_user, monkeypatch: pytest.MonkeyPatch) -> None:
    # We patch the service layer directly to bypass the SQLite incompatibilities in the repo layer
    # and explicitly verify the API serialization of the trend_direction field.
    from app.services.analytics_service import AnalyticsService
    from app.schemas.analytics import SegmentTrendsRead, HourlyTrend, TrendDirection
    
    seg_id = uuid.uuid4()
    
    from tests.conftest import login_user
    
    admin_token = await login_user(client, "admin@example.com", "AdminPass1")
    
    async def mock_get_segment_trends(self, segment_id: uuid.UUID) -> SegmentTrendsRead:
        return SegmentTrendsRead(
            segment_id=segment_id,
            hourly_trends=[
                HourlyTrend(
                    hour_of_day=8,
                    current_avg_vehicle_count=110.0,
                    prior_avg_vehicle_count=100.0,
                    delta_percent=10.0,
                    trend_direction=TrendDirection.INCREASING,
                ),
                HourlyTrend(
                    hour_of_day=9,
                    current_avg_vehicle_count=90.0,
                    prior_avg_vehicle_count=100.0,
                    delta_percent=-10.0,
                    trend_direction=TrendDirection.DECREASING,
                ),
                HourlyTrend(
                    hour_of_day=10,
                    current_avg_vehicle_count=100.0,
                    prior_avg_vehicle_count=100.0,
                    delta_percent=0.0,
                    trend_direction=TrendDirection.STABLE,
                ),
            ]
        )
    
    monkeypatch.setattr(AnalyticsService, "get_segment_trends", mock_get_segment_trends)
    
    response = await client.get(
        f"/api/v1/analytics/segments/{seg_id}/trends",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "hourly_trends" in data
    assert len(data["hourly_trends"]) == 3
    
    trends = data["hourly_trends"]
    assert trends[0]["trend_direction"] == "INCREASING"
    assert trends[1]["trend_direction"] == "DECREASING"
    assert trends[2]["trend_direction"] == "STABLE"
    
    # Check existing fields are still there
    assert trends[0]["delta_percent"] == 10.0
    assert trends[0]["current_avg_vehicle_count"] == 110.0

