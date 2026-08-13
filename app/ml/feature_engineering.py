"""
app/ml/feature_engineering.py

Feature engineering for the TrafficVision ML prediction engine.

Transforms TrafficReading ORM objects into a flat feature matrix
suitable for scikit-learn estimators.

Feature set (deterministic):
  - hour_of_day         : int  [0-23]    hour extracted from recorded_at
  - day_of_week         : int  [0-6]     Monday=0, Sunday=6
  - vehicle_count       : float          raw vehicle count
  - average_speed_kmh   : float          raw speed
  - occupancy_percent   : float          0.0 when NULL (imputed)
  - congestion_ordinal  : int  [0-4]     FREE_FLOW=0 .. STANDSTILL=4

Target (for regression):
  - average_speed_kmh   : float  (speed at prediction horizon)

Congestion classification from predicted speed uses existing
CongestionLevel thresholds relative to the segment speed limit.

No database access occurs in this module.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.models.reading import TrafficReading

# ── Congestion ordinal mapping ────────────────────────────────────────────────

_CONGESTION_ORDINAL: dict[str, int] = {
    "FREE_FLOW": 0,
    "LIGHT": 1,
    "MODERATE": 2,
    "HEAVY": 3,
    "STANDSTILL": 4,
}

_ORDINAL_TO_CONGESTION: dict[int, str] = {v: k for k, v in _CONGESTION_ORDINAL.items()}

# ── Minimum training samples required ────────────────────────────────────────

MIN_TRAINING_SAMPLES: int = 5


# ── Public API ────────────────────────────────────────────────────────────────


def readings_to_feature_matrix(
    readings: "Sequence[TrafficReading]",
) -> tuple[np.ndarray, np.ndarray]:
    """
    Convert a sequence of TrafficReading ORM objects into a (X, y) pair.

    X shape: (n_samples, 6)
    y shape: (n_samples,)  — target: average_speed_kmh

    Args:
        readings: Ordered sequence of TrafficReading objects.

    Returns:
        (X, y) numpy arrays ready for scikit-learn.

    Raises:
        ValueError: If readings is empty.
    """
    if not readings:
        raise ValueError("Cannot build feature matrix from empty readings sequence.")

    X_rows: list[list[float]] = []
    y_vals: list[float] = []

    for r in readings:
        dt = r.recorded_at
        X_rows.append([
            float(dt.hour),
            float(dt.weekday()),
            float(r.vehicle_count),
            float(r.average_speed_kmh),
            float(r.occupancy_percent) if r.occupancy_percent is not None else 0.0,
            float(_CONGESTION_ORDINAL.get(r.congestion_level.value
                  if hasattr(r.congestion_level, "value")
                  else str(r.congestion_level), 0)),
        ])
        y_vals.append(float(r.average_speed_kmh))

    return np.array(X_rows, dtype=np.float64), np.array(y_vals, dtype=np.float64)


def build_inference_features(
    hour_of_day: int,
    day_of_week: int,
    vehicle_count: float,
    average_speed_kmh: float,
    occupancy_percent: float | None,
    congestion_level_value: str,
) -> np.ndarray:
    """
    Build a single-row feature matrix for inference.

    Args:
        hour_of_day:        Target hour to predict for [0-23].
        day_of_week:        Target day of week [0-6].
        vehicle_count:      Latest observed vehicle count.
        average_speed_kmh:  Latest observed average speed.
        occupancy_percent:  Latest observed occupancy (None → 0.0).
        congestion_level_value: String value of CongestionLevel enum.

    Returns:
        numpy array of shape (1, 6).
    """
    return np.array([[
        float(hour_of_day),
        float(day_of_week),
        float(vehicle_count),
        float(average_speed_kmh),
        float(occupancy_percent) if occupancy_percent is not None else 0.0,
        float(_CONGESTION_ORDINAL.get(congestion_level_value, 0)),
    ]], dtype=np.float64)


def classify_congestion(predicted_speed: float, speed_limit_kmh: int) -> str:
    """
    Classify a predicted speed into a CongestionLevel string value.

    Uses the thresholds defined in the Engineering Design Document:
      FREE_FLOW  : speed > 80% of limit
      LIGHT      : 60-80% of limit
      MODERATE   : 40-60% of limit
      HEAVY      : 20-40% of limit
      STANDSTILL : < 20% of limit

    Args:
        predicted_speed:  Predicted average speed in km/h.
        speed_limit_kmh:  Posted speed limit for the segment.

    Returns:
        CongestionLevel string value.
    """
    if speed_limit_kmh <= 0:
        return "MODERATE"
    if predicted_speed <= 0.0:
        return "STANDSTILL"

    ratio = predicted_speed / speed_limit_kmh
    if ratio > 0.80:
        return "FREE_FLOW"
    if ratio > 0.60:
        return "LIGHT"
    if ratio > 0.40:
        return "MODERATE"
    if ratio > 0.20:
        return "HEAVY"
    return "STANDSTILL"
