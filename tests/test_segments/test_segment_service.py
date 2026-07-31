"""
tests/test_segments/test_segment_service.py
"""
import uuid
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import SegmentNotFoundError
from app.models.segment import SegmentStatus, TrafficSegment
from app.schemas.segment import SegmentCreate, SegmentUpdate
from app.services.segment_service import SegmentService


def make_mock_segment(segment_id: uuid.UUID) -> TrafficSegment:
    return TrafficSegment(
        id=segment_id,
        name="Segment 1",
        start_point="Start",
        end_point="End",
        start_latitude=10.0,
        start_longitude=20.0,
        end_latitude=11.0,
        end_longitude=21.0,
        length_km=5.0,
        speed_limit_kmh=60,
        status=SegmentStatus.ACTIVE,
    )


@pytest.fixture
def mock_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_camera_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_reading_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def segment_service(mock_repo: AsyncMock, mock_camera_repo: AsyncMock, mock_reading_repo: AsyncMock) -> SegmentService:
    return SegmentService(segment_repo=mock_repo, camera_repo=mock_camera_repo, reading_repo=mock_reading_repo)


@pytest.mark.asyncio
async def test_get_segment_success(segment_service: SegmentService, mock_repo: AsyncMock) -> None:
    sid = uuid.uuid4()
    mock_segment = make_mock_segment(sid)
    mock_repo.get_by_id.return_value = mock_segment

    result = await segment_service.get_segment(sid)
    assert result.id == sid
    mock_repo.get_by_id.assert_awaited_once_with(sid)


@pytest.mark.asyncio
async def test_get_segment_not_found(segment_service: SegmentService, mock_repo: AsyncMock) -> None:
    sid = uuid.uuid4()
    mock_repo.get_by_id.return_value = None

    with pytest.raises(SegmentNotFoundError):
        await segment_service.get_segment(sid)


@pytest.mark.asyncio
async def test_create_segment(segment_service: SegmentService, mock_repo: AsyncMock) -> None:
    data = SegmentCreate(
        name="Segment 1",
        start_point="Point A",
        end_point="Point B",
        start_latitude=10.0,
        start_longitude=20.0,
        end_latitude=11.0,
        end_longitude=21.0,
        length_km=5.0,
        speed_limit_kmh=60,
        status=SegmentStatus.ACTIVE,
    )
    mock_repo.create.return_value = make_mock_segment(uuid.uuid4())
    
    await segment_service.create_segment(data)
    mock_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_segment(segment_service: SegmentService, mock_repo: AsyncMock) -> None:
    sid = uuid.uuid4()
    mock_segment = make_mock_segment(sid)
    mock_repo.get_by_id.return_value = mock_segment
    mock_repo.update.return_value = mock_segment
    
    data = SegmentUpdate(name="New Name")
    await segment_service.update_segment(sid, data)
    
    mock_repo.get_by_id.assert_awaited_once_with(sid)
    mock_repo.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_segment(segment_service: SegmentService, mock_repo: AsyncMock) -> None:
    sid = uuid.uuid4()
    mock_segment = make_mock_segment(sid)
    mock_repo.get_by_id.return_value = mock_segment
    
    await segment_service.delete_segment(sid)
    mock_repo.get_by_id.assert_awaited_once_with(sid)
    mock_repo.soft_delete.assert_awaited_once_with(mock_segment)
