"""
tests/test_forecast/test_forecast_service.py

Integration tests for PredictionService.run_forecast using a real SQLite DB.
"""
import datetime
import uuid
from datetime import UTC, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InsufficientReadingsError, SegmentNotFoundError
from app.models.prediction import PredictionStatus
from app.models.segment import CongestionLevel, TrafficSegment
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.reading_repository import ReadingRepository
from app.repositories.segment_repository import SegmentRepository
from app.services.prediction_service import PredictionService


@pytest_asyncio.fixture
async def segment(test_db: AsyncSession) -> TrafficSegment:
    seg = TrafficSegment(
        name="Forecast Segment",
        start_point="X",
        end_point="Y",
        start_latitude=40.0,
        start_longitude=-73.0,
        end_latitude=40.1,
        end_longitude=-73.1,
        length_km=3.0,
        speed_limit_kmh=60,
    )
    test_db.add(seg)
    await test_db.commit()
    await test_db.refresh(seg)
    return seg


async def _seed_readings(
    test_db: AsyncSession,
    segment_id: uuid.UUID,
    count: int = 20,
) -> None:
    """Create `count` synthetic readings for training."""
    reading_repo = ReadingRepository(test_db)
    base = datetime.datetime.now(UTC)
    for i in range(count):
        congestion = [
            CongestionLevel.FREE_FLOW,
            CongestionLevel.LIGHT,
            CongestionLevel.MODERATE,
            CongestionLevel.HEAVY,
            CongestionLevel.STANDSTILL,
        ][i % 5]
        await reading_repo.create(
            segment_id=segment_id,
            vehicle_count=20 + i * 3,
            average_speed_kmh=10.0 + i * 3.0,
            congestion_level=congestion,
            occupancy_percent=0.1 + (i % 10) * 0.08,
            recorded_at=base - timedelta(hours=i),
        )
    await test_db.commit()


def _service(test_db: AsyncSession) -> PredictionService:
    return PredictionService(
        PredictionRepository(test_db),
        SegmentRepository(test_db),
        ReadingRepository(test_db),
    )


class TestRunForecast:
    async def test_run_forecast_completes(
        self, test_db: AsyncSession, segment: TrafficSegment
    ) -> None:
        await _seed_readings(test_db, segment.id, count=20)
        service = _service(test_db)
        prediction = await service.run_forecast(segment_id=segment.id, horizon_minutes=60)
        assert prediction.status == PredictionStatus.COMPLETED
        assert prediction.predicted_congestion_level is not None
        assert prediction.predicted_avg_speed_kmh >= 0.0
        assert prediction.model_version is not None
        assert prediction.model_version.startswith("rf-v2-")

    async def test_run_forecast_insufficient_data_raises(
        self, test_db: AsyncSession, segment: TrafficSegment
    ) -> None:
        # Only 2 readings — below MIN_TRAINING_SAMPLES
        await _seed_readings(test_db, segment.id, count=2)
        service = _service(test_db)
        with pytest.raises(InsufficientReadingsError):
            await service.run_forecast(segment_id=segment.id, horizon_minutes=30)

    async def test_run_forecast_bad_segment_raises(self, test_db: AsyncSession) -> None:
        service = _service(test_db)
        with pytest.raises(SegmentNotFoundError):
            await service.run_forecast(segment_id=uuid.uuid4(), horizon_minutes=60)

    async def test_run_forecast_horizon_affects_prediction_for(
        self, test_db: AsyncSession, segment: TrafficSegment
    ) -> None:
        await _seed_readings(test_db, segment.id, count=15)
        service = _service(test_db)
        before = datetime.datetime.now(UTC)
        prediction = await service.run_forecast(segment_id=segment.id, horizon_minutes=120)
        assert prediction.horizon_minutes == 120
        # prediction_for should be roughly 120 min from now
        diff = prediction.prediction_for.replace(tzinfo=UTC) - before
        assert 110 <= diff.total_seconds() / 60 <= 130

    async def test_run_forecast_persisted_in_db(
        self, test_db: AsyncSession, segment: TrafficSegment
    ) -> None:
        await _seed_readings(test_db, segment.id, count=20)
        service = _service(test_db)
        prediction = await service.run_forecast(segment_id=segment.id, horizon_minutes=60)
        # Verify it was persisted
        repo = PredictionRepository(test_db)
        retrieved = await repo.get_by_id(prediction.id)
        assert retrieved is not None
        assert retrieved.status == PredictionStatus.COMPLETED
