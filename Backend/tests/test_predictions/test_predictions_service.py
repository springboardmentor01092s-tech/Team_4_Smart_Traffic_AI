import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import (
    PredictionNotFoundError,
    PredictionNotPendingError,
    PredictionTimeInPastError,
    SegmentNotFoundError,
)
from app.models.prediction import PredictionStatus
from app.models.segment import CongestionLevel
from app.schemas.prediction import PredictionComplete, PredictionCreate
from app.services.prediction_service import PredictionService

pytestmark = pytest.mark.asyncio


async def test_create_prediction_invalid_segment(test_db):
    # Dummy repos logic: segment not found will be handled by mocking or using real repos with empty DB
    from app.repositories.prediction_repository import PredictionRepository
    from app.repositories.segment_repository import SegmentRepository
    
    service = PredictionService(PredictionRepository(test_db), SegmentRepository(test_db))
    
    data = PredictionCreate(
        segment_id=uuid.uuid4(),
        prediction_for=datetime.now(UTC) + timedelta(hours=1),
        horizon_minutes=30,
    )
    
    with pytest.raises(SegmentNotFoundError):
        await service.create_prediction(data)


async def test_create_prediction_time_in_past(test_db, segment):
    from app.repositories.prediction_repository import PredictionRepository
    from app.repositories.segment_repository import SegmentRepository
    
    service = PredictionService(PredictionRepository(test_db), SegmentRepository(test_db))
    
    data = PredictionCreate(
        segment_id=segment.id,
        prediction_for=datetime.now(UTC) - timedelta(hours=1),
        horizon_minutes=30,
    )
    
    with pytest.raises(PredictionTimeInPastError):
        await service.create_prediction(data)


async def test_complete_prediction(test_db, segment):
    from app.repositories.prediction_repository import PredictionRepository
    from app.repositories.segment_repository import SegmentRepository
    
    service = PredictionService(PredictionRepository(test_db), SegmentRepository(test_db))
    
    data = PredictionCreate(
        segment_id=segment.id,
        prediction_for=datetime.now(UTC) + timedelta(hours=1),
        horizon_minutes=30,
    )
    pred = await service.create_prediction(data)
    
    req_at = pred.requested_at
    
    complete_data = PredictionComplete(
        predicted_congestion_level=CongestionLevel.HEAVY,
        predicted_vehicle_count=100,
        predicted_avg_speed_kmh=40.5,
        confidence_score=0.85,
    )
    
    completed_pred = await service.complete_prediction(pred.id, complete_data)
    assert completed_pred.status == PredictionStatus.COMPLETED
    assert completed_pred.completed_at is not None
    assert completed_pred.requested_at == req_at
    assert completed_pred.predicted_congestion_level == CongestionLevel.HEAVY


async def test_fail_prediction(test_db, segment):
    from app.repositories.prediction_repository import PredictionRepository
    from app.repositories.segment_repository import SegmentRepository
    
    service = PredictionService(PredictionRepository(test_db), SegmentRepository(test_db))
    
    data = PredictionCreate(
        segment_id=segment.id,
        prediction_for=datetime.now(UTC) + timedelta(hours=1),
        horizon_minutes=30,
    )
    pred = await service.create_prediction(data)
    
    failed_pred = await service.fail_prediction(pred.id)
    assert failed_pred.status == PredictionStatus.FAILED
    assert failed_pred.completed_at is not None


async def test_complete_not_pending(test_db, segment):
    from app.repositories.prediction_repository import PredictionRepository
    from app.repositories.segment_repository import SegmentRepository
    
    service = PredictionService(PredictionRepository(test_db), SegmentRepository(test_db))
    
    data = PredictionCreate(
        segment_id=segment.id,
        prediction_for=datetime.now(UTC) + timedelta(hours=1),
        horizon_minutes=30,
    )
    pred = await service.create_prediction(data)
    await service.fail_prediction(pred.id)
    
    complete_data = PredictionComplete(
        predicted_congestion_level=CongestionLevel.HEAVY,
        confidence_score=0.85,
    )
    
    with pytest.raises(PredictionNotPendingError):
        await service.complete_prediction(pred.id, complete_data)
