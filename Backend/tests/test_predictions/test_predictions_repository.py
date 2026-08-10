import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prediction import PredictionStatus, TrafficPrediction
from app.models.segment import TrafficSegment
from app.repositories.prediction_repository import PredictionRepository

pytestmark = pytest.mark.asyncio




async def test_create_prediction(test_db: AsyncSession, segment: TrafficSegment):
    repo = PredictionRepository(test_db)
    pred_time = datetime.now(UTC) + timedelta(hours=1)
    
    pred = await repo.create(
        segment_id=segment.id,
        prediction_for=pred_time,
        horizon_minutes=60,
        model_version="v1",
    )
    
    assert pred.id is not None
    assert pred.segment_id == segment.id
    assert pred.status == PredictionStatus.PENDING
    assert pred.requested_at is not None
    assert pred.completed_at is None
    assert pred.model_version == "v1"


async def test_get_by_id_excludes_soft_deleted(test_db: AsyncSession, segment: TrafficSegment):
    repo = PredictionRepository(test_db)
    pred = await repo.create(
        segment_id=segment.id,
        prediction_for=datetime.now(UTC) + timedelta(hours=1),
        horizon_minutes=60,
    )
    
    # Exists initially
    fetched = await repo.get_by_id(pred.id)
    assert fetched is not None
    
    # Soft delete
    await repo.soft_delete(pred)
    
    # Should not be found
    fetched_after = await repo.get_by_id(pred.id)
    assert fetched_after is None


async def test_get_upcoming_for_segment(test_db: AsyncSession, segment: TrafficSegment):
    repo = PredictionRepository(test_db)
    now = datetime.now(UTC)
    
    # 1. Past prediction
    await repo.create(segment_id=segment.id, prediction_for=now - timedelta(hours=1), horizon_minutes=60)
    
    # 2. Upcoming prediction (PENDING)
    upcoming1 = await repo.create(segment_id=segment.id, prediction_for=now + timedelta(hours=1), horizon_minutes=60)
    
    # 3. Upcoming prediction (FAILED) -> Should NOT be returned
    failed = await repo.create(segment_id=segment.id, prediction_for=now + timedelta(hours=2), horizon_minutes=60)
    await repo.update(failed, status=PredictionStatus.FAILED)
    
    # 4. Soft-deleted upcoming -> Should NOT be returned
    deleted = await repo.create(segment_id=segment.id, prediction_for=now + timedelta(hours=3), horizon_minutes=60)
    await repo.soft_delete(deleted)
    
    upcoming = await repo.get_upcoming_for_segment(segment.id)
    assert len(upcoming) == 1
    assert upcoming[0].id == upcoming1.id
