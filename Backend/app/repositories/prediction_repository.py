import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prediction import PredictionStatus, TrafficPrediction

logger = logging.getLogger(__name__)


class PredictionRepository:
    """
    Repository for managing TrafficPrediction entities.
    Filters out soft-deleted records (deleted_at IS NOT NULL) on all read operations.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, prediction_id: uuid.UUID) -> TrafficPrediction | None:
        result = await self._db.execute(
            select(TrafficPrediction).where(
                TrafficPrediction.id == prediction_id,
                TrafficPrediction.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        segment_id: uuid.UUID | None = None,
        status: PredictionStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[TrafficPrediction]:
        stmt = select(TrafficPrediction).where(TrafficPrediction.deleted_at.is_(None))
        
        if segment_id:
            stmt = stmt.where(TrafficPrediction.segment_id == segment_id)
        if status:
            stmt = stmt.where(TrafficPrediction.status == status)
            
        stmt = stmt.order_by(TrafficPrediction.created_at.desc()).offset(skip).limit(limit)
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def get_upcoming_for_segment(self, segment_id: uuid.UUID) -> Sequence[TrafficPrediction]:
        now = datetime.now(UTC)
        stmt = (
            select(TrafficPrediction)
            .where(
                TrafficPrediction.segment_id == segment_id,
                TrafficPrediction.deleted_at.is_(None),
                TrafficPrediction.prediction_for > now,
                TrafficPrediction.status.in_([PredictionStatus.PENDING, PredictionStatus.COMPLETED])
            )
            .order_by(TrafficPrediction.prediction_for.asc())
        )
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def create(
        self,
        *,
        segment_id: uuid.UUID,
        prediction_for: datetime,
        horizon_minutes: int,
        model_version: str | None = None,
    ) -> TrafficPrediction:
        prediction = TrafficPrediction(
            segment_id=segment_id,
            prediction_for=prediction_for,
            horizon_minutes=horizon_minutes,
            model_version=model_version,
            status=PredictionStatus.PENDING,
        )
        self._db.add(prediction)
        await self._db.flush()
        await self._db.refresh(prediction)
        logger.info("TrafficPrediction created | id=%s", prediction.id)
        return prediction

    async def update(self, prediction: TrafficPrediction, **fields: object) -> TrafficPrediction:
        for field, value in fields.items():
            setattr(prediction, field, value)
        self._db.add(prediction)
        await self._db.flush()
        await self._db.refresh(prediction)
        logger.info("TrafficPrediction updated | id=%s", prediction.id)
        return prediction

    async def soft_delete(self, prediction: TrafficPrediction) -> None:
        now = datetime.now(UTC)
        prediction.deleted_at = now
        prediction.updated_at = now
        self._db.add(prediction)
        await self._db.flush()
        logger.warning("TrafficPrediction soft-deleted | id=%s", prediction.id)
