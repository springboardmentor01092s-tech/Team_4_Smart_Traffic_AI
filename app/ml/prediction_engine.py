"""
app/ml/prediction_engine.py

Prediction Engine for TrafficVision AI — Milestone 2.

Responsibilities:
  - Train a RandomForestRegressor on historical TrafficReading data.
  - Compute evaluation metrics (MAE, R2).
  - Run inference to produce predicted traffic metrics.
  - Track model version.
  - Remain entirely independent of FastAPI, SQLAlchemy, and routers.

Design:
  - PredictionEngine holds a TrafficModelProtocol instance.
  - The engine is constructed once per forecast request (stateless MVP).
  - Training and inference are explicitly separated methods.

Known limitations (MVP):
  - The model is trained in-memory per forecast request.
  - There is no persistent model artifact storage in Milestone 2.
  - Model is lightweight (RandomForest n_estimators=50) to keep
    per-request latency acceptable for an MVP workflow.
  - If training data is insufficient (< MIN_TRAINING_SAMPLES), a
    InsufficientTrainingDataError is raised.
"""
from __future__ import annotations

import hashlib
import logging
from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from app.ml.feature_engineering import (
    MIN_TRAINING_SAMPLES,
    build_inference_features,
    classify_congestion,
    readings_to_feature_matrix,
)

if TYPE_CHECKING:
    from app.models.reading import TrafficReading

logger = logging.getLogger(__name__)

_MODEL_ALGORITHM = "RandomForestRegressor"
_N_ESTIMATORS = 50
_RANDOM_STATE = 42


class InsufficientTrainingDataError(Exception):
    """Raised when there are not enough readings to train the model."""

    def __init__(self, actual: int, required: int) -> None:
        super().__init__(
            f"Insufficient training data: {actual} readings available, "
            f"{required} required."
        )
        self.actual = actual
        self.required = required


class PredictionEngine:
    """
    Trains and runs inference using a RandomForestRegressor.

    Usage:
        engine = PredictionEngine()
        engine.train(historical_readings)
        result = engine.predict(
            target_hour=9,
            target_dow=0,
            latest_reading=...,
            speed_limit_kmh=60,
        )
    """

    def __init__(self) -> None:
        self._model: RandomForestRegressor | None = None
        self._model_version: str | None = None
        self._mae: float | None = None
        self._r2: float | None = None
        self._is_trained: bool = False

    # ── Training ──────────────────────────────────────────────────────────────

    def train(self, readings: Sequence["TrafficReading"]) -> None:
        """
        Train the RandomForestRegressor on historical traffic readings.

        Args:
            readings: Sequence of TrafficReading ORM objects.

        Raises:
            InsufficientTrainingDataError: If fewer than MIN_TRAINING_SAMPLES.
        """
        n = len(readings)
        if n < MIN_TRAINING_SAMPLES:
            raise InsufficientTrainingDataError(actual=n, required=MIN_TRAINING_SAMPLES)

        X, y = readings_to_feature_matrix(readings)

        # Evaluation split only when we have enough data; otherwise fit on all.
        if n >= 10:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=_RANDOM_STATE
            )
        else:
            X_train, y_train = X, y
            X_test, y_test = X, y

        model = RandomForestRegressor(
            n_estimators=_N_ESTIMATORS,
            random_state=_RANDOM_STATE,
        )
        model.fit(X_train, y_train)

        y_pred_test = model.predict(X_test)
        self._mae = float(mean_absolute_error(y_test, y_pred_test))
        self._r2 = float(r2_score(y_test, y_pred_test))

        self._model = model
        self._model_version = self._compute_version(readings)
        self._is_trained = True

        logger.info(
            "PredictionEngine trained | samples=%d | MAE=%.3f | R2=%.3f | version=%s",
            n,
            self._mae,
            self._r2,
            self._model_version,
        )

    # ── Inference ─────────────────────────────────────────────────────────────

    def predict(
        self,
        *,
        target_hour: int,
        target_day_of_week: int,
        latest_vehicle_count: float,
        latest_speed_kmh: float,
        latest_occupancy: float | None,
        latest_congestion_value: str,
        speed_limit_kmh: int,
    ) -> dict:
        """
        Run inference to produce predicted traffic metrics.

        Args:
            target_hour:              Hour of day to predict for [0-23].
            target_day_of_week:       Day of week [0-6].
            latest_vehicle_count:     Most recent vehicle count observation.
            latest_speed_kmh:         Most recent speed observation.
            latest_occupancy:         Most recent occupancy (None → 0.0).
            latest_congestion_value:  CongestionLevel string value.
            speed_limit_kmh:          Posted speed limit for the segment.

        Returns:
            dict with keys:
              predicted_avg_speed_kmh : float
              predicted_vehicle_count : int
              predicted_congestion_level : str (CongestionLevel value)
              confidence_score        : float [0.0-1.0]
              model_version           : str

        Raises:
            RuntimeError: If called before train().
        """
        if not self._is_trained or self._model is None:
            raise RuntimeError("PredictionEngine.predict() called before train().")

        X_infer = build_inference_features(
            hour_of_day=target_hour,
            day_of_week=target_day_of_week,
            vehicle_count=latest_vehicle_count,
            average_speed_kmh=latest_speed_kmh,
            occupancy_percent=latest_occupancy,
            congestion_level_value=latest_congestion_value,
        )

        predicted_speed = float(self._model.predict(X_infer)[0])
        predicted_speed = max(0.0, predicted_speed)

        congestion_str = classify_congestion(predicted_speed, speed_limit_kmh)

        # Vehicle count: scale proportionally from speed ratio change.
        # If speed drops, count tends to rise — a defensible heuristic.
        speed_ratio = (predicted_speed / latest_speed_kmh) if latest_speed_kmh > 0 else 1.0
        predicted_count = max(0, int(latest_vehicle_count / max(speed_ratio, 0.1)))

        confidence = self._compute_confidence()

        return {
            "predicted_avg_speed_kmh": round(predicted_speed, 2),
            "predicted_vehicle_count": predicted_count,
            "predicted_congestion_level": congestion_str,
            "confidence_score": round(confidence, 4),
            "model_version": self._model_version or "unknown",
        }

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def model_version(self) -> str | None:
        return self._model_version

    @property
    def mae(self) -> float | None:
        return self._mae

    @property
    def r2(self) -> float | None:
        return self._r2

    @property
    def is_trained(self) -> bool:
        return self._is_trained

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_version(readings: Sequence["TrafficReading"]) -> str:
        """
        Deterministically derive a model version string from the training data.

        Version format: rf-v2-{n_samples}-{data_hash[:8]}
        This allows downstream systems to detect when the model was retrained
        on a different dataset without storing a separate model artifact.
        """
        ids = "-".join(str(r.id) for r in readings[:10])
        data_hash = hashlib.sha256(
            f"{len(readings)}-{ids}".encode()
        ).hexdigest()
        return f"rf-v2-{len(readings)}-{data_hash[:8]}"

    def _compute_confidence(self) -> float:
        """
        Derive a confidence score from evaluation metrics.

        Maps R² to [0.0, 1.0]:
          R² >= 0.9  → confidence >= 0.9
          R² <= 0.0  → confidence = 0.3 (minimum non-trivial confidence)

        If R² is unavailable, return 0.5 (baseline).
        """
        if self._r2 is None:
            return 0.5
        # Clamp R² to [0, 1], then map to [0.3, 0.95].
        r2_clamped = max(0.0, min(1.0, self._r2))
        return round(0.3 + r2_clamped * 0.65, 4)
