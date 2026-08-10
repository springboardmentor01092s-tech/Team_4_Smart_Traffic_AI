"""
tests/test_segments/test_segment_repository.py
"""
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.segment import SegmentStatus, TrafficSegment
from app.repositories.segment_repository import SegmentRepository


async def make_segment(
    repo: SegmentRepository,
    *,
    name: str = "Test Segment",
    start_point: str = "Start",
    end_point: str = "End",
    start_latitude: float = 28.61,
    start_longitude: float = 77.20,
    end_latitude: float = 28.65,
    end_longitude: float = 77.08,
    length_km: float = 5.0,
    speed_limit_kmh: int = 60,
    status: SegmentStatus = SegmentStatus.ACTIVE,
    camera_id: uuid.UUID | None = None,
) -> TrafficSegment:
    return await repo.create(
        name=name,
        start_point=start_point,
        end_point=end_point,
        start_latitude=start_latitude,
        start_longitude=start_longitude,
        end_latitude=end_latitude,
        end_longitude=end_longitude,
        length_km=length_km,
        speed_limit_kmh=speed_limit_kmh,
        status=status,
        camera_id=camera_id,
    )


@pytest.mark.asyncio
async def test_create_segment(test_db: AsyncSession) -> None:
    repo = SegmentRepository(test_db)
    segment = await make_segment(repo, name="Segment A")
    
    assert segment.id is not None
    assert segment.name == "Segment A"
    assert segment.status == SegmentStatus.ACTIVE


@pytest.mark.asyncio
async def test_get_by_id(test_db: AsyncSession) -> None:
    repo = SegmentRepository(test_db)
    segment = await make_segment(repo)
    
    fetched = await repo.get_by_id(segment.id)
    assert fetched is not None
    assert fetched.id == segment.id


@pytest.mark.asyncio
async def test_get_by_id_soft_deleted(test_db: AsyncSession) -> None:
    repo = SegmentRepository(test_db)
    segment = await make_segment(repo)
    await repo.soft_delete(segment)
    
    fetched = await repo.get_by_id(segment.id)
    assert fetched is None


@pytest.mark.asyncio
async def test_get_all(test_db: AsyncSession) -> None:
    repo = SegmentRepository(test_db)
    seg1 = await make_segment(repo, name="Seg 1")
    seg2 = await make_segment(repo, name="Seg 2")
    
    segments = await repo.get_all()
    ids = {s.id for s in segments}
    assert seg1.id in ids
    assert seg2.id in ids


@pytest.mark.asyncio
async def test_get_all_excludes_soft_deleted(test_db: AsyncSession) -> None:
    repo = SegmentRepository(test_db)
    active_seg = await make_segment(repo, name="Active")
    deleted_seg = await make_segment(repo, name="Deleted")
    await repo.soft_delete(deleted_seg)
    
    segments = await repo.get_all()
    ids = {s.id for s in segments}
    assert active_seg.id in ids
    assert deleted_seg.id not in ids


@pytest.mark.asyncio
async def test_update_segment(test_db: AsyncSession) -> None:
    repo = SegmentRepository(test_db)
    segment = await make_segment(repo, speed_limit_kmh=60)
    
    updated = await repo.update(segment, speed_limit_kmh=80)
    assert updated.speed_limit_kmh == 80


@pytest.mark.asyncio
async def test_soft_delete(test_db: AsyncSession) -> None:
    repo = SegmentRepository(test_db)
    segment = await make_segment(repo)
    assert segment.deleted_at is None
    
    await repo.soft_delete(segment)
    assert segment.deleted_at is not None


@pytest.mark.asyncio
async def test_get_all_filters_by_status(test_db: AsyncSession) -> None:
    repo = SegmentRepository(test_db)
    active_seg = await make_segment(repo, name="Active Seg", status=SegmentStatus.ACTIVE)
    inactive_seg = await make_segment(repo, name="Inactive Seg", status=SegmentStatus.INACTIVE)
    
    segments = await repo.get_all(status=SegmentStatus.INACTIVE)
    ids = {s.id for s in segments}
    assert inactive_seg.id in ids
    assert active_seg.id not in ids


@pytest.mark.asyncio
async def test_get_all_filters_by_camera_id(test_db: AsyncSession) -> None:
    repo = SegmentRepository(test_db)
    cam_id_1 = uuid.uuid4()
    cam_id_2 = uuid.uuid4()
    
    seg1 = await make_segment(repo, name="Seg 1", camera_id=cam_id_1)
    seg2 = await make_segment(repo, name="Seg 2", camera_id=cam_id_2)
    
    segments = await repo.get_all(camera_id=cam_id_1)
    ids = {s.id for s in segments}
    assert seg1.id in ids
    assert seg2.id not in ids
