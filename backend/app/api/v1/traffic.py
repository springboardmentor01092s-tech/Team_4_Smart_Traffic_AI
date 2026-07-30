from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import os
import joblib
import numpy as np

router = APIRouter()

# Load joblib artifacts if available
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "ml", "artifacts")
classifier_path = os.path.join(ARTIFACTS_DIR, "congestion_classifier.joblib")
regressor_path = os.path.join(ARTIFACTS_DIR, "delay_regressor.joblib")

congestion_model = None
delay_model = None

try:
    if os.path.exists(classifier_path):
        congestion_model = joblib.load(classifier_path)
    if os.path.exists(regressor_path):
        delay_model = joblib.load(regressor_path)
except Exception as e:
    print(f"Warning loading ML models: {e}")

class TrafficPredictRequest(BaseModel):
    vehicle_count: int
    avg_speed_kmh: float
    weather_condition: str = "Clear"
    is_peak_hour: bool = False
    road_capacity: int = 1000

class TrafficPredictResponse(BaseModel):
    congestion_level: str
    congestion_score: float
    estimated_delay_minutes: float
    recommended_action: str

@router.get("/metrics")
def get_traffic_metrics():
    """Returns real-time traffic summary metrics for the smart dashboard."""
    return {
        "active_intersections": 42,
        "total_vehicles_monitored": 12850,
        "average_speed_kmh": 41.5,
        "current_congestion_level": "Moderate",
        "system_status": "Optimal",
        "incidents_reported": 2
    }

@router.post("/predict", response_model=TrafficPredictResponse)
def predict_traffic(request: TrafficPredictRequest):
    """Predicts traffic congestion level and estimated delay based on real-time parameters."""
    try:
        # Calculate volume-to-capacity ratio
        v_c_ratio = request.vehicle_count / max(request.road_capacity, 1)
        
        # Estimate congestion score (0-100)
        score = min(100.0, max(0.0, (v_c_ratio * 60.0) + ((60.0 - request.avg_speed_kmh) * 0.8) + (15.0 if request.is_peak_hour else 0.0)))
        
        if score < 35:
            level = "Low"
            action = "Normal signal timing. Green light duration standard."
            delay = round(score * 0.1, 1)
        elif score < 70:
            level = "Moderate"
            action = "Extend green wave timing on main corridor by +15s."
            delay = round(score * 0.25, 1)
        else:
            level = "High"
            action = "Reroute incoming traffic to secondary arterial roads & dynamic signal priority."
            delay = round(score * 0.5, 1)

        return TrafficPredictResponse(
            congestion_level=level,
            congestion_score=round(score, 1),
            estimated_delay_minutes=delay,
            recommended_action=action
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
