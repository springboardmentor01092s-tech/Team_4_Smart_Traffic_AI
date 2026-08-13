"""
tests/test_prediction_report/test_prediction_report.py

Integration tests for GET /api/v1/analytics/predictions.
"""
import datetime
import uuid
from datetime import UTC, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prediction import PredictionStatus
from app.models.segment import CongestionLevel, TrafficSegment
from app.repositories.prediction_repository import PredictionRepository
from tests.conftest import login_user, make_auth_headers


@pytest_asyncio.fixture
async def segment_with_predictions(test_db: AsyncSession):
    seg = TrafficSegment(
        name="Report Segment", start_point="A", end_point="B",
        start_latitude=10.0, start_longitude=10.0,
        end_latitude=11.0, end_longitude=11.0,
        length_km=5.0, speed_limit_kmh=60,
    )
    test_db.add(seg)
    await test_db.commit()
    await test_db.refresh(seg)

    repo = PredictionRepository(test_db)
    now = datetime.datetime.now(UTC)
    # 2 completed, 1 failed, 1 pending
    p1 = await repo.create(
        segment_id=seg.id, prediction_for=now + timedelta(hours=1),
        horizon_minutes=60, model_version="rf-v2-20-abc",
    )
    await repo.update(
        p1, status=PredictionStatus.COMPLETED, completed_at=now,
        predicted_congestion_level=CongestionLevel.MODERATE,
        predicted_vehicle_count=50, predicted_avg_speed_kmh=40.0,
        confidence_score=0.85,
    )
    p2 = await repo.create(
        segment_id=seg.id, prediction_for=now + timedelta(hours=2),
        horizon_minutes=120, model_version="rf-v2-20-abc",
    )
    await repo.update(
        p2, status=PredictionStatus.COMPLETED, completed_at=now,
        predicted_congestion_level=CongestionLevel.LIGHT,
        predicted_vehicle_count=30, predicted_avg_speed_kmh=55.0,
        confidence_score=0.9,
    )
    p3 = await repo.create(
        segment_id=seg.id, prediction_for=now + timedelta(hours=3),
        horizon_minutes=60, model_version="rf-v2-20-abc",
    )
    await repo.update(p3, status=PredictionStatus.FAILED, completed_at=now)

    await repo.create(
        segment_id=seg.id, prediction_for=now + timedelta(hours=4),
        horizon_minutes=60, model_version=None,
    )  # pending

    await test_db.commit()
    return seg


class TestPredictionReportRouter:
    async def test_report_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/analytics/predictions")
        assert resp.status_code == 403

    async def test_report_requires_tc_or_admin(
        self, client: AsyncClient, segment_with_predictions, public_user
    ) -> None:
        token = await login_user(client, "testuser@example.com", "TestPass1")
        resp = await client.get(
            "/api/v1/analytics/predictions",
            headers=make_auth_headers(token),
        )
        assert resp.status_code == 403

    async def test_report_success_as_admin(
        self, client: AsyncClient, segment_with_predictions, admin_user
    ) -> None:
        token = await login_user(client, "admin@example.com", "AdminPass1")
        resp = await client.get(
            "/api/v1/analytics/predictions",
            headers=make_auth_headers(token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total_predictions"] == 4
        assert body["completed"] == 2
        assert body["failed"] == 1
        assert body["pending"] == 1
        assert body["completion_rate"] == pytest.approx(0.5, abs=0.01)
        assert len(body["predictions"]) == 4

    async def test_report_filter_by_status(
        self, client: AsyncClient, segment_with_predictions, traffic_controller_user
    ) -> None:
        token = await login_user(client, "controller@example.com", "ControllerPass1")
        resp = await client.get(
            "/api/v1/analytics/predictions",
            params={"status": "COMPLETED"},
            headers=make_auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_predictions"] == 2
        assert body["completed"] == 2

    async def test_report_filter_by_segment(
        self, client: AsyncClient, segment_with_predictions, admin_user
    ) -> None:
        token = await login_user(client, "admin@example.com", "AdminPass1")
        seg = segment_with_predictions
        resp = await client.get(
            "/api/v1/analytics/predictions",
            params={"segment_id": str(seg.id)},
            headers=make_auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_predictions"] == 4  # all 4 belong to this segment

    async def test_report_pagination(
        self, client: AsyncClient, segment_with_predictions, admin_user
    ) -> None:
        token = await login_user(client, "admin@example.com", "AdminPass1")
        resp = await client.get(
            "/api/v1/analytics/predictions",
            params={"limit": 2, "skip": 0},
            headers=make_auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_predictions"] == 2
