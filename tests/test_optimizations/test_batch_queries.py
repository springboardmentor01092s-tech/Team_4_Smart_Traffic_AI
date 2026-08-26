"""
tests/test_optimizations/test_batch_queries.py

Unit tests verifying batch query repository methods (ReadingRepository, SegmentRepository, RouteRepository)
and regression safety of the N+1 optimization.
"""
import uuid
from datetime import UTC, datetime
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reading import TrafficReading
from app.models.route import Route, RouteSegment
from app.models.segment import CongestionLevel, TrafficSegment
from app.repositories.reading_repository import ReadingRepository
from app.repositories.route_repository import RouteRepository
from app.repositories.segment_repository import SegmentRepository
from app.services.route_service import RouteService


@pytest.mark.asyncio
async def test_batch_reading_and_segment_lookups(test_db: AsyncSession) -> None:
    """Verify get_latest_for_segments and get_by_ids return correct mappings in single queries."""
    reading_repo = ReadingRepository(test_db)
    segment_repo = SegmentRepository(test_db)
    route_repo = RouteRepository(test_db)

    # 1. Create 3 segments
    seg1 = TrafficSegment(
        name="Seg 1", start_point="A", end_point="B",
        start_latitude=40.0, start_longitude=-74.0,
        end_latitude=40.1, end_longitude=-74.1,
        length_km=10.0, speed_limit_kmh=60
    )
    seg2 = TrafficSegment(
        name="Seg 2", start_point="B", end_point="C",
        start_latitude=40.1, start_longitude=-74.1,
        end_latitude=40.2, end_longitude=-74.2,
        length_km=15.0, speed_limit_kmh=80
    )
    seg3 = TrafficSegment(
        name="Seg 3", start_point="C", end_point="D",
        start_latitude=40.2, start_longitude=-74.2,
        end_latitude=40.3, end_longitude=-74.3,
        length_km=5.0, speed_limit_kmh=50
    )
    test_db.add_all([seg1, seg2, seg3])
    await test_db.flush()

    # 2. Add multiple readings for seg1 and seg2, none for seg3
    now = datetime.now(UTC)
    r1_old = TrafficReading(
        segment_id=seg1.id, vehicle_count=50, average_speed_kmh=55.0,
        congestion_level=CongestionLevel.LIGHT, recorded_at=now.replace(hour=8)
    )
    r1_latest = TrafficReading(
        segment_id=seg1.id, vehicle_count=120, average_speed_kmh=35.0,
        congestion_level=CongestionLevel.HEAVY, recorded_at=now.replace(hour=9)
    )
    r2_latest = TrafficReading(
        segment_id=seg2.id, vehicle_count=80, average_speed_kmh=75.0,
        congestion_level=CongestionLevel.FREE_FLOW, recorded_at=now.replace(hour=9)
    )
    test_db.add_all([r1_old, r1_latest, r2_latest])
    await test_db.commit()

    # Test get_by_ids on segments
    segments_map = await segment_repo.get_by_ids([seg1.id, seg2.id, seg3.id, uuid.uuid4()])
    assert len(segments_map) == 3
    assert segments_map[seg1.id].name == "Seg 1"
    assert segments_map[seg2.id].name == "Seg 2"
    assert segments_map[seg3.id].name == "Seg 3"

    # Test get_latest_for_segments
    readings_map = await reading_repo.get_latest_for_segments([seg1.id, seg2.id, seg3.id])
    assert len(readings_map) == 2
    assert readings_map[seg1.id].vehicle_count == 120
    assert readings_map[seg1.id].average_speed_kmh == 35.0
    assert readings_map[seg2.id].vehicle_count == 80
    assert seg3.id not in readings_map

    # Test batch empty inputs
    assert await reading_repo.get_latest_for_segments([]) == {}
    assert await segment_repo.get_by_ids([]) == {}
    assert await route_repo.get_by_ids([]) == {}


@pytest.mark.asyncio
async def test_route_service_batch_travel_time_equivalence(test_db: AsyncSession) -> None:
    """Verify estimate_travel_time calculation accuracy with mixed readings and fallback to speed limit."""
    reading_repo = ReadingRepository(test_db)
    segment_repo = SegmentRepository(test_db)
    route_repo = RouteRepository(test_db)
    service = RouteService(route_repo, segment_repo, reading_repo)

    # Create a route with 2 segments
    route = Route(
        name="Express Highway",
        origin_name="City A",
        destination_name="City B",
        total_distance_km=30.0,
    )
    test_db.add(route)
    await test_db.flush()

    seg1 = TrafficSegment(
        name="Seg 1 (Reading)", start_point="A", end_point="B",
        start_latitude=40.0, start_longitude=-74.0,
        end_latitude=40.1, end_longitude=-74.1,
        length_km=10.0, speed_limit_kmh=60
    )
    seg2 = TrafficSegment(
        name="Seg 2 (Fallback)", start_point="B", end_point="C",
        start_latitude=40.1, start_longitude=-74.1,
        end_latitude=40.2, end_longitude=-74.2,
        length_km=20.0, speed_limit_kmh=100
    )
    test_db.add_all([seg1, seg2])
    await test_db.flush()

    rs1 = RouteSegment(route_id=route.id, segment_id=seg1.id, sequence_order=1)
    rs2 = RouteSegment(route_id=route.id, segment_id=seg2.id, sequence_order=2)
    test_db.add_all([rs1, rs2])

    # Add reading for seg1 only (avg speed = 30 km/h -> 10km at 30km/h = 20 min)
    reading1 = TrafficReading(
        segment_id=seg1.id, vehicle_count=150, average_speed_kmh=30.0,
        congestion_level=CongestionLevel.MODERATE, recorded_at=datetime.now(UTC)
    )
    test_db.add(reading1)
    await test_db.commit()

    # Seg2 fallback: 20km at 100km/h = 12 min
    # Total expected: 20 min + 12 min = 32.00 min
    estimate = await service.estimate_travel_time(route.id)
    assert estimate.estimated_travel_minutes == 32.00
    assert estimate.segment_count == 2
    assert estimate.segments_with_readings == 1
    assert estimate.worst_congestion_level == CongestionLevel.MODERATE
    assert estimate.segment_estimates[0].data_source == "reading"
    assert estimate.segment_estimates[1].data_source == "speed_limit"
