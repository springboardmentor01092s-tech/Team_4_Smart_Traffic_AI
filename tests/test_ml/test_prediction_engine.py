"""
tests/test_ml/test_prediction_engine.py

Unit tests for PredictionEngine.
"""
import datetime
from unittest.mock import MagicMock

import pytest

from app.ml.prediction_engine import InsufficientTrainingDataError, PredictionEngine


def _make_reading(
    id: int = 1,
    hour: int = 8,
    day: int = 15,
    vehicle_count: int = 50,
    speed: float = 40.0,
    occupancy: float | None = 0.5,
    congestion: str = "MODERATE",
) -> MagicMock:
    """Minimal TrafficReading mock."""
    dt = datetime.datetime(2024, 1, day, hour, 0, 0, tzinfo=datetime.timezone.utc)
    r = MagicMock()
    r.id = id
    r.recorded_at = dt
    r.vehicle_count = vehicle_count
    r.average_speed_kmh = speed
    r.occupancy_percent = occupancy
    cong = MagicMock()
    cong.value = congestion
    r.congestion_level = cong
    return r


def _make_readings(n: int = 20) -> list[MagicMock]:
    """Generate n distinct readings with varying speeds."""
    return [
        _make_reading(
            id=i,
            hour=i % 24,
            day=15 + (i % 14),
            vehicle_count=20 + i * 2,
            speed=10.0 + i * 2.5,
            occupancy=0.1 + (i % 10) * 0.08,
            congestion=["FREE_FLOW", "LIGHT", "MODERATE", "HEAVY", "STANDSTILL"][i % 5],
        )
        for i in range(n)
    ]


class TestPredictionEngineTrain:
    def test_raises_on_insufficient_data(self) -> None:
        engine = PredictionEngine()
        readings = _make_readings(3)  # < MIN_TRAINING_SAMPLES (5)
        with pytest.raises(InsufficientTrainingDataError):
            engine.train(readings)

    def test_trains_successfully(self) -> None:
        engine = PredictionEngine()
        readings = _make_readings(20)
        engine.train(readings)
        assert engine.is_trained is True
        assert engine.model_version is not None
        assert engine.model_version.startswith("rf-v2-")
        assert engine.mae is not None
        assert engine.mae >= 0.0

    def test_model_version_deterministic(self) -> None:
        readings = _make_readings(15)
        e1 = PredictionEngine()
        e1.train(readings)
        e2 = PredictionEngine()
        e2.train(readings)
        assert e1.model_version == e2.model_version

    def test_minimum_samples_boundary(self) -> None:
        """Exactly MIN_TRAINING_SAMPLES should train without error."""
        from app.ml.feature_engineering import MIN_TRAINING_SAMPLES
        readings = _make_readings(MIN_TRAINING_SAMPLES)
        engine = PredictionEngine()
        engine.train(readings)
        assert engine.is_trained


class TestPredictionEnginePredict:
    def setup_method(self) -> None:
        self.engine = PredictionEngine()
        self.engine.train(_make_readings(25))

    def test_predict_returns_expected_keys(self) -> None:
        result = self.engine.predict(
            target_hour=9,
            target_day_of_week=0,
            latest_vehicle_count=50.0,
            latest_speed_kmh=40.0,
            latest_occupancy=0.4,
            latest_congestion_value="MODERATE",
            speed_limit_kmh=60,
        )
        assert "predicted_avg_speed_kmh" in result
        assert "predicted_vehicle_count" in result
        assert "predicted_congestion_level" in result
        assert "confidence_score" in result
        assert "model_version" in result

    def test_predict_speed_non_negative(self) -> None:
        result = self.engine.predict(
            target_hour=2,
            target_day_of_week=6,
            latest_vehicle_count=200.0,
            latest_speed_kmh=5.0,
            latest_occupancy=0.9,
            latest_congestion_value="STANDSTILL",
            speed_limit_kmh=60,
        )
        assert result["predicted_avg_speed_kmh"] >= 0.0

    def test_predict_before_train_raises(self) -> None:
        engine = PredictionEngine()
        with pytest.raises(RuntimeError, match="before train"):
            engine.predict(
                target_hour=9,
                target_day_of_week=0,
                latest_vehicle_count=50.0,
                latest_speed_kmh=40.0,
                latest_occupancy=None,
                latest_congestion_value="MODERATE",
                speed_limit_kmh=60,
            )

    def test_confidence_in_range(self) -> None:
        result = self.engine.predict(
            target_hour=12,
            target_day_of_week=1,
            latest_vehicle_count=30.0,
            latest_speed_kmh=55.0,
            latest_occupancy=0.3,
            latest_congestion_value="LIGHT",
            speed_limit_kmh=80,
        )
        assert 0.0 <= result["confidence_score"] <= 1.0

    def test_congestion_level_valid(self) -> None:
        result = self.engine.predict(
            target_hour=8,
            target_day_of_week=0,
            latest_vehicle_count=80.0,
            latest_speed_kmh=30.0,
            latest_occupancy=0.7,
            latest_congestion_value="HEAVY",
            speed_limit_kmh=60,
        )
        valid = {"FREE_FLOW", "LIGHT", "MODERATE", "HEAVY", "STANDSTILL"}
        assert result["predicted_congestion_level"] in valid
