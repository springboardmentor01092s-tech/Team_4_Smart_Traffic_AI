"""
tests/test_ml/test_feature_engineering.py

Unit tests for app/ml/feature_engineering.py.
Pure Python — no DB, no FastAPI.
"""
import datetime
from unittest.mock import MagicMock

import numpy as np
import pytest

from app.ml.feature_engineering import (
    MIN_TRAINING_SAMPLES,
    build_inference_features,
    classify_congestion,
    readings_to_feature_matrix,
)


def _make_reading(
    hour: int = 8,
    weekday: int = 0,
    vehicle_count: int = 50,
    speed: float = 40.0,
    occupancy: float | None = 0.5,
    congestion: str = "MODERATE",
) -> MagicMock:
    """Build a minimal TrafficReading mock."""
    dt = datetime.datetime(2024, 1, 15, hour, 0, 0, tzinfo=datetime.timezone.utc)
    # Adjust weekday via date — Monday=0
    dt = dt.replace(day=15 + weekday)

    r = MagicMock()
    r.recorded_at = dt
    r.vehicle_count = vehicle_count
    r.average_speed_kmh = speed
    r.occupancy_percent = occupancy
    cong_mock = MagicMock()
    cong_mock.value = congestion
    r.congestion_level = cong_mock
    return r


class TestReadingsToFeatureMatrix:
    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            readings_to_feature_matrix([])

    def test_single_reading(self) -> None:
        r = _make_reading(hour=9, weekday=1, vehicle_count=30, speed=50.0, occupancy=0.3, congestion="LIGHT")
        X, y = readings_to_feature_matrix([r])
        assert X.shape == (1, 6)
        assert y.shape == (1,)
        # hour
        assert X[0, 0] == pytest.approx(9.0)
        # vehicle_count
        assert X[0, 2] == pytest.approx(30.0)
        # speed
        assert X[0, 3] == pytest.approx(50.0)
        # occupancy
        assert X[0, 4] == pytest.approx(0.3)
        # congestion ordinal for LIGHT = 1
        assert X[0, 5] == pytest.approx(1.0)
        # target
        assert y[0] == pytest.approx(50.0)

    def test_null_occupancy_imputed_zero(self) -> None:
        r = _make_reading(occupancy=None)
        X, _ = readings_to_feature_matrix([r])
        assert X[0, 4] == pytest.approx(0.0)

    def test_multiple_readings_shape(self) -> None:
        readings = [_make_reading(speed=float(i * 10)) for i in range(1, 11)]
        X, y = readings_to_feature_matrix(readings)
        assert X.shape == (10, 6)
        assert y.shape == (10,)

    def test_standstill_ordinal(self) -> None:
        r = _make_reading(congestion="STANDSTILL")
        X, _ = readings_to_feature_matrix([r])
        assert X[0, 5] == pytest.approx(4.0)

    def test_free_flow_ordinal(self) -> None:
        r = _make_reading(congestion="FREE_FLOW")
        X, _ = readings_to_feature_matrix([r])
        assert X[0, 5] == pytest.approx(0.0)


class TestBuildInferenceFeatures:
    def test_shape(self) -> None:
        X = build_inference_features(
            hour_of_day=12,
            day_of_week=2,
            vehicle_count=40.0,
            average_speed_kmh=55.0,
            occupancy_percent=0.4,
            congestion_level_value="MODERATE",
        )
        assert X.shape == (1, 6)

    def test_values(self) -> None:
        X = build_inference_features(
            hour_of_day=7,
            day_of_week=4,
            vehicle_count=100.0,
            average_speed_kmh=25.0,
            occupancy_percent=None,
            congestion_level_value="HEAVY",
        )
        assert X[0, 0] == pytest.approx(7.0)   # hour
        assert X[0, 1] == pytest.approx(4.0)   # dow
        assert X[0, 2] == pytest.approx(100.0) # vehicle_count
        assert X[0, 3] == pytest.approx(25.0)  # speed
        assert X[0, 4] == pytest.approx(0.0)   # occupancy (None -> 0.0)
        assert X[0, 5] == pytest.approx(3.0)   # HEAVY = 3


class TestClassifyCongestion:
    @pytest.mark.parametrize("speed, limit, expected", [
        (85.0,  100, "FREE_FLOW"),
        (70.0,  100, "LIGHT"),
        (50.0,  100, "MODERATE"),
        (30.0,  100, "HEAVY"),
        (10.0,  100, "STANDSTILL"),
        (0.0,   100, "STANDSTILL"),
        (55.0,   60, "FREE_FLOW"),
        (100.0,   0, "MODERATE"),  # zero speed_limit edge case
    ])
    def test_classify(self, speed: float, limit: int, expected: str) -> None:
        assert classify_congestion(speed, limit) == expected
