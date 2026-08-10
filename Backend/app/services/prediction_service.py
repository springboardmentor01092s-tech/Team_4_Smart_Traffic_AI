import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from app.core.exceptions import (
    PredictionNotFoundError,
    PredictionNotPendingError,
    PredictionTimeInPastError,
    SegmentNotFoundError,
)
from app.models.prediction import PredictionStatus, TrafficPrediction
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.segment_repository import SegmentRepository
from app.schemas.prediction import PredictionComplete, PredictionCreate


class PredictionService:
    """
    Business logic layer for managing TrafficPredictions.
    """

    def __init__(
        self,
        prediction_repo: PredictionRepository,
        segment_repo: SegmentRepository,
    ) -> None:
        self._prediction_repo = prediction_repo
        self._segment_repo = segment_repo

    async def list_predictions(
        self,
        segment_id: uuid.UUID | None = None,
        status: PredictionStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[TrafficPrediction]:
        if segment_id:
            segment = await self._segment_repo.get_by_id(segment_id)
            if not segment:
                raise SegmentNotFoundError(segment_id)

        return await self._prediction_repo.get_all(
            segment_id=segment_id,
            status=status,
            skip=skip,
            limit=limit,
        )

    async def get_prediction(self, prediction_id: uuid.UUID) -> TrafficPrediction:
        prediction = await self._prediction_repo.get_by_id(prediction_id)
        if not prediction:
            raise PredictionNotFoundError(prediction_id)
        return prediction

    async def get_upcoming_for_segment(self, segment_id: uuid.UUID) -> Sequence[TrafficPrediction]:
        segment = await self._segment_repo.get_by_id(segment_id)
        if not segment:
            raise SegmentNotFoundError(segment_id)

        return await self._prediction_repo.get_upcoming_for_segment(segment_id)

    async def create_prediction(self, data: PredictionCreate) -> TrafficPrediction:
        segment = await self._segment_repo.get_by_id(data.segment_id)
        if not segment:
            raise SegmentNotFoundError(data.segment_id)

        if data.prediction_for <= datetime.now(UTC):
            raise PredictionTimeInPastError()

        return await self._prediction_repo.create(
            segment_id=data.segment_id,
            prediction_for=data.prediction_for,
            horizon_minutes=data.horizon_minutes,
            model_version=data.model_version,
        )

    async def complete_prediction(
        self, prediction_id: uuid.UUID, data: PredictionComplete
    ) -> TrafficPrediction:
        prediction = await self.get_prediction(prediction_id)

        if prediction.status != PredictionStatus.PENDING:
            raise PredictionNotPendingError(prediction_id)

        return await self._prediction_repo.update(
            prediction,
            predicted_congestion_level=data.predicted_congestion_level,
            predicted_vehicle_count=data.predicted_vehicle_count,
            predicted_avg_speed_kmh=data.predicted_avg_speed_kmh,
            confidence_score=data.confidence_score,
            status=PredictionStatus.COMPLETED,
            completed_at=datetime.now(UTC),
        )

    async def fail_prediction(self, prediction_id: uuid.UUID) -> TrafficPrediction:
        prediction = await self.get_prediction(prediction_id)

        if prediction.status != PredictionStatus.PENDING:
            raise PredictionNotPendingError(prediction_id)

        return await self._prediction_repo.update(
            prediction,
            status=PredictionStatus.FAILED,
            completed_at=datetime.now(UTC),
        )

    async def delete_prediction(self, prediction_id: uuid.UUID) -> None:
        prediction = await self.get_prediction(prediction_id)
        await self._prediction_repo.soft_delete(prediction)
