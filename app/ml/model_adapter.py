"""
app/ml/model_adapter.py

Abstract model adapter protocol for TrafficVision AI ML.

Defines the interface that any prediction model must satisfy.
This allows the underlying algorithm (currently RandomForestRegressor)
to be replaced without changing PredictionService or the router.
"""
from __future__ import annotations

from typing import Protocol

import numpy as np


class TrafficModelProtocol(Protocol):
    """
    Protocol defining the interface for a traffic prediction model.

    Any class implementing this protocol can be used as the model
    inside PredictionEngine without changes to the service layer.
    """

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train the model on feature matrix X and target vector y."""
        ...

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Return predictions for feature matrix X."""
        ...
