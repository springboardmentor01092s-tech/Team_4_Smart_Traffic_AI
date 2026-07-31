from datetime import datetime, timezone, timedelta
import uuid
import pytest
from unittest.mock import AsyncMock

from app.core.exceptions import InvalidReadingTimeError, SegmentNotFoundError
from app.models.segment import CongestionLevel, TrafficSegment
from app.models.reading import TrafficReading
from app.schemas.reading import ReadingCreate
from app.services.reading_service import ReadingService


@pytest.fixture
def mock_reading_repo():
    return AsyncMock()


@pytest.fixture
def mock_segment_repo():
    return AsyncMock()


@pytest.fixture
def reading_service(mock_reading_repo, mock_segment_repo):
    return ReadingService(mock_reading_repo, mock_segment_repo)


@pytest.mark.asyncio
async def test_submit_reading_success(reading_service, mock_segment_repo, mock_reading_repo):
    segment_id = uuid.uuid4()
    mock_segment_repo.get_by_id.return_value = TrafficSegment(id=segment_id)

    data = ReadingCreate(
        segment_id=segment_id,
        vehicle_count=100,
        average_speed_kmh=40.0,
        congestion_level=CongestionLevel.MODERATE,
        occupancy_percent=30.0,
        recorded_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )

    mock_reading_repo.create.return_value = TrafficReading(id=1, **data.model_dump())

    reading = await reading_service.submit_reading(data)
    assert reading.id == 1
    mock_reading_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_submit_reading_invalid_time(reading_service, mock_segment_repo, mock_reading_repo):
    segment_id = uuid.uuid4()
    mock_segment_repo.get_by_id.return_value = TrafficSegment(id=segment_id)

    data = ReadingCreate(
        segment_id=segment_id,
        vehicle_count=100,
        average_speed_kmh=40.0,
        congestion_level=CongestionLevel.MODERATE,
        occupancy_percent=30.0,
        recorded_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )

    with pytest.raises(InvalidReadingTimeError):
        await reading_service.submit_reading(data)


@pytest.mark.asyncio
async def test_submit_reading_segment_not_found(reading_service, mock_segment_repo):
    segment_id = uuid.uuid4()
    mock_segment_repo.get_by_id.return_value = None

    data = ReadingCreate(
        segment_id=segment_id,
        vehicle_count=100,
        average_speed_kmh=40.0,
        congestion_level=CongestionLevel.MODERATE,
        recorded_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )

    with pytest.raises(SegmentNotFoundError):
        await reading_service.submit_reading(data)
