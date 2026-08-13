"""
tests/test_forecast/test_forecast_router.py

Integration tests for POST /api/v1/predictions/segment/{id}/forecast.
"""
import datetime
import uuid
from datetime import UTC, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.segment import CongestionLevel, TrafficSegment
from app.repositories.reading_repository import ReadingRepository
from tests.conftest import login_user, make_auth_headers


@pytest_asyncio.fixture
async def segment(test_db: AsyncSession) -> TrafficSegment:
    seg = TrafficSegment(
        name="Router Forecast Segment",
        start_point="A",
        end_point="B",
        start_latitude=51.0,
        start_longitude=-0.1,
        end_latitude=51.1,
        end_longitude=-0.2,
        length_km=5.0,
        speed_limit_kmh=80,
    )
    test_db.add(seg)
    await test_db.commit()
    await test_db.refresh(seg)
    return seg


async def _seed_readings(
    test_db: AsyncSession, segment_id: uuid.UUID, count: int = 20
) -> None:
    repo = ReadingRepository(test_db)
    base = datetime.datetime.now(UTC)
    congestion_levels = [
        CongestionLevel.FREE_FLOW, CongestionLevel.LIGHT, CongestionLevel.MODERATE,
        CongestionLevel.HEAVY, CongestionLevel.STANDSTILL,
    ]
    for i in range(count):
        await repo.create(
            segment_id=segment_id,
            vehicle_count=20 + i * 3,
            average_speed_kmh=10.0 + i * 3.5,
            congestion_level=congestion_levels[i % 5],
            occupancy_percent=0.1 + (i % 10) * 0.08,
            recorded_at=base - timedelta(hours=i),
        )
    await test_db.commit()


class TestForecastRouter:
    async def test_forecast_requires_auth(
        self, client: AsyncClient, segment: TrafficSegment
    ) -> None:
        resp = await client.post(
            f"/api/v1/predictions/segment/{segment.id}/forecast",
            json={"horizon_minutes": 60},
        )
        assert resp.status_code == 403

    async def test_forecast_requires_tc_or_admin(
        self, client: AsyncClient, segment: TrafficSegment,
        test_db: AsyncSession, public_user
    ) -> None:
        await _seed_readings(test_db, segment.id, 20)
        token = await login_user(client, "testuser@example.com", "TestPass1")
        resp = await client.post(
            f"/api/v1/predictions/segment/{segment.id}/forecast",
            json={"horizon_minutes": 60},
            headers=make_auth_headers(token),
        )
        assert resp.status_code == 403

    async def test_forecast_success_as_admin(
        self, client: AsyncClient, segment: TrafficSegment,
        test_db: AsyncSession, admin_user
    ) -> None:
        await _seed_readings(test_db, segment.id, 20)
        token = await login_user(client, "admin@example.com", "AdminPass1")
        resp = await client.post(
            f"/api/v1/predictions/segment/{segment.id}/forecast",
            json={"horizon_minutes": 60},
            headers=make_auth_headers(token),
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "COMPLETED"
        assert body["segment_id"] == str(segment.id)
        assert body["predicted_avg_speed_kmh"] >= 0.0
        assert body["model_version"] is not None

    async def test_forecast_success_as_traffic_controller(
        self, client: AsyncClient, segment: TrafficSegment,
        test_db: AsyncSession, traffic_controller_user
    ) -> None:
        await _seed_readings(test_db, segment.id, 20)
        token = await login_user(client, "controller@example.com", "ControllerPass1")
        resp = await client.post(
            f"/api/v1/predictions/segment/{segment.id}/forecast",
            json={"horizon_minutes": 30},
            headers=make_auth_headers(token),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["horizon_minutes"] == 30

    async def test_forecast_insufficient_readings_returns_422(
        self, client: AsyncClient, segment: TrafficSegment,
        test_db: AsyncSession, admin_user
    ) -> None:
        # Only 2 readings — too few
        await _seed_readings(test_db, segment.id, 2)
        token = await login_user(client, "admin@example.com", "AdminPass1")
        resp = await client.post(
            f"/api/v1/predictions/segment/{segment.id}/forecast",
            json={"horizon_minutes": 60},
            headers=make_auth_headers(token),
        )
        assert resp.status_code == 422
        assert "INSUFFICIENT_READINGS" in resp.json()["error_code"]

    async def test_forecast_unknown_segment_returns_404(
        self, client: AsyncClient, admin_user
    ) -> None:
        token = await login_user(client, "admin@example.com", "AdminPass1")
        resp = await client.post(
            f"/api/v1/predictions/segment/{uuid.uuid4()}/forecast",
            json={"horizon_minutes": 60},
            headers=make_auth_headers(token),
        )
        assert resp.status_code == 404

    async def test_forecast_invalid_horizon_returns_422(
        self, client: AsyncClient, segment: TrafficSegment, admin_user
    ) -> None:
        token = await login_user(client, "admin@example.com", "AdminPass1")
        resp = await client.post(
            f"/api/v1/predictions/segment/{segment.id}/forecast",
            json={"horizon_minutes": 0},  # must be > 0
            headers=make_auth_headers(token),
        )
        assert resp.status_code == 422
