"""
app/services/prediction_service.py

Business logic layer for managing TrafficPredictions.

Milestone 2 additions:
  - run_forecast(): orchestrates ML training + inference for a segment,
    then persists the result using the existing PENDING -> COMPLETED/FAILED
    lifecycle.
"""
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from app.core.exceptions import (
    InsufficientReadingsError,
    PredictionNotFoundError,
    PredictionNotPendingError,
    PredictionTimeInPastError,
    SegmentNotFoundError,
)
from app.core.logging import get_logger
from app.ml.feature_engineering import MIN_TRAINING_SAMPLES
from app.ml.prediction_engine import InsufficientTrainingDataError, PredictionEngine
from app.models.prediction import PredictionStatus, TrafficPrediction
from app.models.segment import CongestionLevel
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.reading_repository import ReadingRepository
from app.repositories.segment_repository import SegmentRepository
from app.schemas.prediction import PredictionComplete, PredictionCreate

logger = get_logger(__name__)

# Maximum historical window to fetch for training (90 days)
_TRAINING_WINDOW_DAYS = 90
# Maximum readings to pull for training (caps memory usage)
_TRAINING_MAX_READINGS = 2000


class PredictionService:
    """
    Business logic layer for managing TrafficPredictions.

    Constructor args (all required):
      prediction_repo  - PredictionRepository
      segment_repo     - SegmentRepository
      reading_repo     - ReadingRepository (required for run_forecast)
    """

    def __init__(
        self,
        prediction_repo: PredictionRepository,
        segment_repo: SegmentRepository,
        reading_repo: ReadingRepository | None = None,
    ) -> None:
        self._prediction_repo = prediction_repo
        self._segment_repo = segment_repo
        self._reading_repo = reading_repo

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

    # ── Milestone 2: ML-powered forecast ─────────────────────────────────────

    async def run_forecast(
        self,
        segment_id: uuid.UUID,
        horizon_minutes: int,
    ) -> TrafficPrediction:
        """
        Execute an ML-powered congestion forecast for a segment.

        Flow:
          1. Validate segment exists (non-deleted).
          2. Fetch historical readings as training data.
          3. Validate sufficient data exists.
          4. Create TrafficPrediction record with status=PENDING.
          5. Train PredictionEngine on historical readings.
          6. Determine inference context from the latest reading.
          7. Run inference.
          8. On success: update prediction to COMPLETED with results.
          9. On failure: update prediction to FAILED.
         10. Return final prediction.

        Args:
            segment_id:       UUID of the target segment.
            horizon_minutes:  How many minutes into the future to forecast.

        Returns:
            Completed (or failed) TrafficPrediction.

        Raises:
            SegmentNotFoundError:      Segment does not exist.
            InsufficientReadingsError: Not enough readings to train.
        """
        if self._reading_repo is None:
            raise RuntimeError(
                "run_forecast requires ReadingRepository. "
                "Inject it via get_forecast_service dependency."
            )

        # Step 1: Validate segment
        segment = await self._segment_repo.get_by_id(segment_id)
        if not segment:
            raise SegmentNotFoundError(segment_id)

        # Step 2: Fetch historical readings for training
        now = datetime.now(UTC)
        from_dt = now - timedelta(days=_TRAINING_WINDOW_DAYS)
        readings = await self._reading_repo.get_all(
            segment_id=segment_id,
            from_dt=from_dt,
            to_dt=now,
            limit=_TRAINING_MAX_READINGS,
        )

        # Step 3: Validate sufficient data
        n_readings = len(readings)
        if n_readings < MIN_TRAINING_SAMPLES:
            raise InsufficientReadingsError(
                segment_id=segment_id,
                actual=n_readings,
                required=MIN_TRAINING_SAMPLES,
            )

        # Step 4: Create PENDING prediction
        prediction_for = now + timedelta(minutes=horizon_minutes)
        prediction = await self._prediction_repo.create(
            segment_id=segment_id,
            prediction_for=prediction_for,
            horizon_minutes=horizon_minutes,
            model_version=None,  # will be set after training
        )

        try:
            # Step 5: Train the engine
            engine = PredictionEngine()
            engine.train(readings)

            # Step 6: Determine inference context from latest reading
            latest = readings[0]  # get_all orders by desc(recorded_at)
            target_dt = prediction_for
            congestion_value = (
                latest.congestion_level.value
                if hasattr(latest.congestion_level, "value")
                else str(latest.congestion_level)
            )

            # Step 7: Run inference
            result = engine.predict(
                target_hour=target_dt.hour,
                target_day_of_week=target_dt.weekday(),
                latest_vehicle_count=float(latest.vehicle_count),
                latest_speed_kmh=float(latest.average_speed_kmh),
                latest_occupancy=float(latest.occupancy_percent)
                if latest.occupancy_percent is not None
                else None,
                latest_congestion_value=congestion_value,
                speed_limit_kmh=segment.speed_limit_kmh,
            )

            # Resolve CongestionLevel enum member from string
            congestion_enum = CongestionLevel(result["predicted_congestion_level"])

            # Step 8: Mark COMPLETED
            prediction = await self._prediction_repo.update(
                prediction,
                predicted_congestion_level=congestion_enum,
                predicted_vehicle_count=result["predicted_vehicle_count"],
                predicted_avg_speed_kmh=result["predicted_avg_speed_kmh"],
                confidence_score=result["confidence_score"],
                model_version=result["model_version"],
                status=PredictionStatus.COMPLETED,
                completed_at=datetime.now(UTC),
            )

            logger.info(
                "Forecast completed | segment=%s | horizon=%dm | congestion=%s | confidence=%.3f",
                segment_id,
                horizon_minutes,
                result["predicted_congestion_level"],
                result["confidence_score"],
            )

        except (InsufficientTrainingDataError, ValueError, RuntimeError) as exc:
            # Step 9: Mark FAILED on any engine error
            logger.error(
                "Forecast failed | segment=%s | error=%s",
                segment_id,
                exc,
            )
            prediction = await self._prediction_repo.update(
                prediction,
                status=PredictionStatus.FAILED,
                completed_at=datetime.now(UTC),
            )

        return prediction
