from datetime import datetime, timezone, timedelta
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.segment import CongestionLevel, TrafficSegment, SegmentStatus
from app.repositories.reading_repository import ReadingRepository
from app.repositories.segment_repository import SegmentRepository
from app.repositories.camera_repository import CameraRepository
from app.models.camera import TrafficCamera, CameraStatus


@pytest.fixture
async def setup_camera_segment(test_db: AsyncSession):
    camera_repo = CameraRepository(test_db)
    camera = await camera_repo.create(
        name="Test Camera",
        location_name="Test Location",
        latitude=0.0,
        longitude=0.0,
        status=CameraStatus.ACTIVE,
    )
    segment_repo = SegmentRepository(test_db)
    segment = await segment_repo.create(
        name="Test Segment",
        start_point="Start",
        end_point="End",
        start_latitude=0.0,
        start_longitude=0.0,
        end_latitude=1.0,
        end_longitude=1.0,
        length_km=10.0,
        speed_limit_kmh=100,
        camera_id=camera.id,
        status=SegmentStatus.ACTIVE,
    )
    return camera, segment


@pytest.mark.asyncio
async def test_reading_repository_create_and_get(test_db: AsyncSession, setup_camera_segment):
    camera, segment = setup_camera_segment
    repo = ReadingRepository(test_db)

    recorded_at = datetime.now(timezone.utc)
    reading = await repo.create(
        segment_id=segment.id,
        vehicle_count=50,
        average_speed_kmh=80.5,
        congestion_level=CongestionLevel.LIGHT,
        occupancy_percent=20.0,
        recorded_at=recorded_at,
    )

    assert reading.id is not None
    assert reading.segment_id == segment.id
    assert reading.vehicle_count == 50
    assert reading.average_speed_kmh == 80.5
    assert reading.congestion_level == CongestionLevel.LIGHT

    fetched = await repo.get_by_id(reading.id)
    assert fetched is not None
    assert fetched.id == reading.id


@pytest.mark.asyncio
async def test_reading_repository_get_latest(test_db: AsyncSession, setup_camera_segment):
    camera, segment = setup_camera_segment
    repo = ReadingRepository(test_db)

    now = datetime.now(timezone.utc)
    
    await repo.create(
        segment_id=segment.id,
        vehicle_count=10,
        average_speed_kmh=50,
        congestion_level=CongestionLevel.FREE_FLOW,
        occupancy_percent=10,
        recorded_at=now - timedelta(minutes=10),
    )
    
    reading2 = await repo.create(
        segment_id=segment.id,
        vehicle_count=20,
        average_speed_kmh=40,
        congestion_level=CongestionLevel.MODERATE,
        occupancy_percent=30,
        recorded_at=now,
    )

    latest = await repo.get_latest_for_segment(segment.id)
    assert latest is not None
    assert latest.id == reading2.id


@pytest.mark.asyncio
async def test_reading_repository_get_all_filtering(test_db: AsyncSession, setup_camera_segment):
    camera, segment = setup_camera_segment
    repo = ReadingRepository(test_db)

    now = datetime.now(timezone.utc)
    
    await repo.create(segment.id, 10, 50, CongestionLevel.FREE_FLOW, 10, now - timedelta(minutes=10))
    await repo.create(segment.id, 50, 20, CongestionLevel.HEAVY, 60, now - timedelta(minutes=5))
    await repo.create(segment.id, 100, 5, CongestionLevel.STANDSTILL, 90, now)

    readings = await repo.get_all(segment_id=segment.id, congestion_level=CongestionLevel.HEAVY)
    assert len(readings) == 1
    assert readings[0].congestion_level == CongestionLevel.HEAVY

    readings = await repo.get_all(segment_id=segment.id, from_dt=now - timedelta(minutes=6))
    assert len(readings) == 2


@pytest.mark.asyncio
async def test_count_by_congestion_level(test_db: AsyncSession, setup_camera_segment):
    camera, segment1 = setup_camera_segment
    
    segment_repo = SegmentRepository(test_db)
    segment2 = await segment_repo.create(
        name="Seg2", start_point="S", end_point="E", start_latitude=0.0, start_longitude=0.0,
        end_latitude=1.0, end_longitude=1.0, length_km=10.0, speed_limit_kmh=100,
        camera_id=camera.id, status=SegmentStatus.ACTIVE,
    )

    repo = ReadingRepository(test_db)
    now = datetime.now(timezone.utc)

    # Seg1 latest: HEAVY
    await repo.create(segment1.id, 10, 50, CongestionLevel.FREE_FLOW, 10, now - timedelta(minutes=10))
    await repo.create(segment1.id, 50, 20, CongestionLevel.HEAVY, 60, now)

    # Seg2 latest: STANDSTILL
    await repo.create(segment2.id, 100, 5, CongestionLevel.STANDSTILL, 90, now)

    counts = await repo.count_by_congestion_level()
    assert counts[CongestionLevel.HEAVY.value] == 1
    assert counts[CongestionLevel.STANDSTILL.value] == 1
    assert counts[CongestionLevel.FREE_FLOW.value] == 0

    # Soft delete segment 1, it should not be counted
    await segment_repo.soft_delete(segment1)
    
    counts2 = await repo.count_by_congestion_level()
    assert counts2[CongestionLevel.HEAVY.value] == 0
    assert counts2[CongestionLevel.STANDSTILL.value] == 1
