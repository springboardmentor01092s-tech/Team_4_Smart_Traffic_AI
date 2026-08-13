"""
tests/test_route_compare/test_route_compare_router.py

Integration tests for GET /api/v1/routes/compare and GET /routes/{id}/estimate.
"""
import datetime
import uuid
from datetime import UTC

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.route import Route
from app.models.segment import CongestionLevel, TrafficSegment
from app.repositories.reading_repository import ReadingRepository
from app.repositories.route_repository import RouteRepository
from tests.conftest import login_user, make_auth_headers


@pytest_asyncio.fixture
async def populated_route(test_db: AsyncSession):
    seg = TrafficSegment(
        name="Compare Seg", start_point="A", end_point="B",
        start_latitude=10.0, start_longitude=10.0,
        end_latitude=10.1, end_longitude=10.1,
        length_km=8.0, speed_limit_kmh=80,
    )
    test_db.add(seg)
    await test_db.commit()
    await test_db.refresh(seg)

    route = Route(
        name="Compare Route", origin_name="Orig", destination_name="Dest",
        total_distance_km=8.0,
    )
    test_db.add(route)
    await test_db.commit()
    await test_db.refresh(route)

    route_repo = RouteRepository(test_db)
    await route_repo.add_segment(route_id=route.id, segment_id=seg.id, sequence_order=1)

    reading_repo = ReadingRepository(test_db)
    await reading_repo.create(
        segment_id=seg.id, vehicle_count=40,
        average_speed_kmh=60.0, congestion_level=CongestionLevel.LIGHT,
        occupancy_percent=0.3, recorded_at=datetime.datetime.now(UTC),
    )
    await test_db.commit()
    return route


class TestRouteCompareRouter:
    async def test_compare_requires_auth(
        self, client: AsyncClient, populated_route: Route
    ) -> None:
        resp = await client.get(
            "/api/v1/routes/compare",
            params={"route_ids": str(populated_route.id)},
        )
        assert resp.status_code == 403

    async def test_compare_success(
        self, client: AsyncClient, populated_route: Route, public_user
    ) -> None:
        token = await login_user(client, "testuser@example.com", "TestPass1")
        resp = await client.get(
            "/api/v1/routes/compare",
            params={"route_ids": str(populated_route.id)},
            headers=make_auth_headers(token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["recommended_route_id"] == str(populated_route.id)
        assert len(body["routes"]) == 1
        assert body["routes"][0]["is_recommended"] is True

    async def test_compare_no_valid_routes_422(
        self, client: AsyncClient, public_user
    ) -> None:
        token = await login_user(client, "testuser@example.com", "TestPass1")
        resp = await client.get(
            "/api/v1/routes/compare",
            params={"route_ids": str(uuid.uuid4())},
            headers=make_auth_headers(token),
        )
        assert resp.status_code == 422
        assert "NO_VIABLE_ROUTE" in resp.json()["error_code"]


class TestRouteTravelTimeRouter:
    async def test_estimate_requires_auth(
        self, client: AsyncClient, populated_route: Route
    ) -> None:
        resp = await client.get(f"/api/v1/routes/{populated_route.id}/estimate")
        assert resp.status_code == 403

    async def test_estimate_success(
        self, client: AsyncClient, populated_route: Route, public_user
    ) -> None:
        token = await login_user(client, "testuser@example.com", "TestPass1")
        resp = await client.get(
            f"/api/v1/routes/{populated_route.id}/estimate",
            headers=make_auth_headers(token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["route_id"] == str(populated_route.id)
        assert body["estimated_travel_minutes"] > 0
        assert body["segment_count"] == 1
        assert len(body["segment_estimates"]) == 1

    async def test_estimate_unknown_route_404(
        self, client: AsyncClient, public_user
    ) -> None:
        token = await login_user(client, "testuser@example.com", "TestPass1")
        resp = await client.get(
            f"/api/v1/routes/{uuid.uuid4()}/estimate",
            headers=make_auth_headers(token),
        )
        assert resp.status_code == 404
