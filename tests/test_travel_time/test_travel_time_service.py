"""
tests/test_travel_time/test_travel_time_service.py

Integration tests for RouteService.estimate_travel_time.
"""
import datetime
import uuid
from datetime import UTC

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RouteNotFoundError
from app.models.route import Route
from app.models.segment import CongestionLevel, TrafficSegment
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.reading_repository import ReadingRepository
from app.repositories.route_repository import RouteRepository
from app.repositories.segment_repository import SegmentRepository
from app.services.route_service import RouteService


def _service(db: AsyncSession) -> RouteService:
    return RouteService(
        RouteRepository(db),
        SegmentRepository(db),
        ReadingRepository(db),
        PredictionRepository(db),
    )


@pytest_asyncio.fixture
async def route_with_segments(test_db: AsyncSession):
    """Create a route with two segments, each with a reading."""
    seg1 = TrafficSegment(
        name="Seg A", start_point="A", end_point="B",
        start_latitude=40.0, start_longitude=-73.0,
        end_latitude=40.1, end_longitude=-73.1,
        length_km=10.0, speed_limit_kmh=80,
    )
    seg2 = TrafficSegment(
        name="Seg B", start_point="B", end_point="C",
        start_latitude=40.1, start_longitude=-73.1,
        end_latitude=40.2, end_longitude=-73.2,
        length_km=5.0, speed_limit_kmh=60,
    )
    test_db.add_all([seg1, seg2])
    await test_db.commit()
    await test_db.refresh(seg1)
    await test_db.refresh(seg2)

    route = Route(
        name="Test Route",
        origin_name="Origin",
        destination_name="Destination",
        total_distance_km=15.0,
    )
    test_db.add(route)
    await test_db.commit()
    await test_db.refresh(route)

    route_repo = RouteRepository(test_db)
    await route_repo.add_segment(route_id=route.id, segment_id=seg1.id, sequence_order=1)
    await route_repo.add_segment(route_id=route.id, segment_id=seg2.id, sequence_order=2)

    # Add readings: seg1 = 40 km/h, seg2 = 30 km/h
    reading_repo = ReadingRepository(test_db)
    now = datetime.datetime.now(UTC)
    await reading_repo.create(
        segment_id=seg1.id, vehicle_count=50,
        average_speed_kmh=40.0, congestion_level=CongestionLevel.MODERATE,
        occupancy_percent=0.4, recorded_at=now,
    )
    await reading_repo.create(
        segment_id=seg2.id, vehicle_count=80,
        average_speed_kmh=30.0, congestion_level=CongestionLevel.HEAVY,
        occupancy_percent=0.7, recorded_at=now,
    )
    await test_db.commit()
    return route, seg1, seg2


class TestEstimateTravelTime:
    async def test_estimate_uses_reading_speed(
        self, test_db: AsyncSession, route_with_segments
    ) -> None:
        route, seg1, seg2 = route_with_segments
        service = _service(test_db)
        result = await service.estimate_travel_time(route.id)

        # seg1: 10 km / 40 km/h * 60 = 15 min
        # seg2: 5 km / 30 km/h * 60 = 10 min
        # total: 25 min
        assert result.estimated_travel_minutes == pytest.approx(25.0, abs=0.1)
        assert result.route_id == route.id
        assert result.segment_count == 2
        assert result.segments_with_readings == 2
        # worst is HEAVY
        from app.models.segment import CongestionLevel
        assert result.worst_congestion_level == CongestionLevel.HEAVY

    async def test_estimate_falls_back_to_speed_limit(
        self, test_db: AsyncSession
    ) -> None:
        """When no readings exist, speed_limit_kmh is used."""
        seg = TrafficSegment(
            name="No-Reading Seg", start_point="X", end_point="Y",
            start_latitude=1.0, start_longitude=1.0,
            end_latitude=2.0, end_longitude=2.0,
            length_km=6.0, speed_limit_kmh=60,
        )
        test_db.add(seg)
        await test_db.commit()
        await test_db.refresh(seg)

        route = Route(
            name="Speed Limit Route", origin_name="O", destination_name="D",
            total_distance_km=6.0,
        )
        test_db.add(route)
        await test_db.commit()
        await test_db.refresh(route)

        route_repo = RouteRepository(test_db)
        await route_repo.add_segment(route_id=route.id, segment_id=seg.id, sequence_order=1)
        await test_db.commit()

        service = _service(test_db)
        result = await service.estimate_travel_time(route.id)
        # 6 km / 60 km/h * 60 = 6 min
        assert result.estimated_travel_minutes == pytest.approx(6.0, abs=0.1)
        assert result.segments_with_readings == 0
        assert result.segment_estimates[0].data_source == "speed_limit"

    async def test_estimate_unknown_route_raises(self, test_db: AsyncSession) -> None:
        service = _service(test_db)
        with pytest.raises(RouteNotFoundError):
            await service.estimate_travel_time(uuid.uuid4())

    async def test_estimate_response_has_segment_breakdown(
        self, test_db: AsyncSession, route_with_segments
    ) -> None:
        route, seg1, seg2 = route_with_segments
        service = _service(test_db)
        result = await service.estimate_travel_time(route.id)
        assert len(result.segment_estimates) == 2
        for item in result.segment_estimates:
            assert item.estimated_minutes > 0
            assert item.speed_used_kmh > 0


class TestCompareRoutes:
    async def test_compare_returns_recommended(
        self, test_db: AsyncSession, route_with_segments
    ) -> None:
        """Smoke test: compare a single route returns it as recommended."""
        route, *_ = route_with_segments
        service = _service(test_db)
        result = await service.compare_routes([route.id])
        assert result.recommended_route_id == route.id
        assert len(result.routes) == 1
        assert result.routes[0].is_recommended is True

    async def test_compare_unknown_route_skipped(
        self, test_db: AsyncSession, route_with_segments
    ) -> None:
        """Unknown route IDs are silently skipped."""
        route, *_ = route_with_segments
        service = _service(test_db)
        result = await service.compare_routes([route.id, uuid.uuid4()])
        # Only 1 valid route
        assert len(result.routes) == 1

    async def test_compare_no_valid_routes_raises(self, test_db: AsyncSession) -> None:
        from app.core.exceptions import NoViableRouteError
        service = _service(test_db)
        with pytest.raises(NoViableRouteError):
            await service.compare_routes([uuid.uuid4()])
