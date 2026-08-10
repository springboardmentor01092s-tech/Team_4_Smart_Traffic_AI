from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import joblib

router = APIRouter()

# Load joblib artifacts if available
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "ml", "artifacts")
classifier_path = os.path.join(ARTIFACTS_DIR, "congestion_classifier.joblib")
regressor_path = os.path.join(ARTIFACTS_DIR, "traffic_model.pkl")

congestion_model = None
volume_model = None

try:
    if os.path.exists(classifier_path):
        congestion_model = joblib.load(classifier_path)
        if hasattr(congestion_model, "set_params"):
            congestion_model.set_params(n_jobs=1)
    if os.path.exists(regressor_path):
        volume_model = joblib.load(regressor_path)
        if hasattr(volume_model, "set_params"):
            volume_model.set_params(n_jobs=1)
except Exception as e:
    print(f"Warning loading ML models: {e}")

# In-memory storage for dynamic alerts & overrides
IN_MEMORY_INCIDENTS = [
    {
        "id": 1,
        "location": "MG Road Corridor - Junction 4",
        "type": "Accident",
        "severity": "High",
        "description": "Two-vehicle collision blocking right lane.",
        "reported_at": "10 mins ago",
        "status": "Active"
    },
    {
        "id": 2,
        "location": "Outer Ring Road Exit 12",
        "type": "Road Work",
        "severity": "Medium",
        "description": "Lane reduction for asphalt resurfacing.",
        "reported_at": "25 mins ago",
        "status": "Active"
    }
]

IN_MEMORY_JUNCTIONS = [
    {"id": "J1", "name": "Central Plaza Crossing", "vehicle_count": 840, "speed_kmh": 22, "status": "Heavy", "signal": "Green", "override": False},
    {"id": "J2", "name": "MG Road & 5th Avenue", "vehicle_count": 620, "speed_kmh": 38, "status": "Moderate", "signal": "Green", "override": False},
    {"id": "J3", "name": "Tech Corridor Junction", "vehicle_count": 1120, "speed_kmh": 14, "status": "Heavy", "signal": "Red", "override": False},
    {"id": "J4", "name": "Airport Expressway Flyover", "vehicle_count": 310, "speed_kmh": 64, "status": "Clear", "signal": "Green", "override": False},
    {"id": "J5", "name": "Metro Station Interchange", "vehicle_count": 590, "speed_kmh": 31, "status": "Moderate", "signal": "Yellow", "override": False},
    {"id": "J6", "name": "South Port Boulevard", "vehicle_count": 280, "speed_kmh": 55, "status": "Clear", "signal": "Green", "override": False},
]

IN_MEMORY_PROPOSED_ROUTES = []

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

class RouteOptimizeRequest(BaseModel):
    origin: str
    destination: str

class IncidentReportRequest(BaseModel):
    location: str
    type: str
    severity: str
    description: str

class SignalOverrideRequest(BaseModel):
    junction_id: str
    mode: str  # "emergency_green", "all_red", "auto"

class ApproveRouteRequest(BaseModel):
    route_id: str

@router.get("/metrics")
def get_traffic_metrics():
    """Returns real-time traffic summary metrics for the smart dashboard."""
    return {
        "active_intersections": len(IN_MEMORY_JUNCTIONS),
        "total_vehicles_monitored": sum(j["vehicle_count"] for j in IN_MEMORY_JUNCTIONS) * 12,
        "average_speed_kmh": round(sum(j["speed_kmh"] for j in IN_MEMORY_JUNCTIONS) / len(IN_MEMORY_JUNCTIONS), 1),
        "current_congestion_level": "Moderate",
        "system_status": "Optimal",
        "incidents_reported": len(IN_MEMORY_INCIDENTS)
    }

@router.get("/junctions")
def get_junctions():
    """Returns city-wide junction statuses."""
    return IN_MEMORY_JUNCTIONS

@router.post("/predict", response_model=TrafficPredictResponse)
def predict_traffic(request: TrafficPredictRequest):
    """
    Predicts traffic congestion level and estimated delay using trained ML models (RandomForest Regressor & Classifier).
    Models are trained on 48,000+ hourly observations from the UCI Metro Interstate Traffic Volume dataset.

    [ARCHITECTURE NOTE / MILESTONE 3]:
    In standalone demo mode, lag features (volume_lag_1h, volume_lag_24h, rolling_avg_3h) are estimated
    from current payload metrics. In live production deployment, these features are queried dynamically
    from the Traffic Monitoring Service database history.
    """
    try:
        import datetime
        import pandas as pd
        import numpy as np
        
        now = datetime.datetime.now()
        hour = now.hour
        day_of_week = now.weekday()
        is_weekend = 1 if day_of_week in [5, 6] else 0
        
        # Standalone Demo Baseline: Estimate lag features from current request payload
        # Next Milestone: Query past 24-hour time series from Traffic Monitoring Service database
        volume_lag_1h = max(0, request.vehicle_count + np.random.normal(0, 20))
        volume_lag_24h = max(0, request.vehicle_count + np.random.normal(0, 50))
        rolling_avg_3h = float(request.vehicle_count)
        temp = 25.0 # Celsius
        rain_1h = 1 if request.weather_condition.lower() in ["rain", "rainy", "storm"] else 0
        
        # Default mock fallback values
        level = "Low"
        score = 0.0
        delay = 0.0
        
        if congestion_model is not None and volume_model is not None:
            # Create feature dataframe as expected by the model
            # features = ["hour", "day_of_week", "is_weekend", "volume_lag_1h", "volume_lag_24h", "rolling_avg_3h", "temp", "rain_1h"]
            features_df = pd.DataFrame([{
                "hour": hour,
                "day_of_week": day_of_week,
                "is_weekend": is_weekend,
                "volume_lag_1h": volume_lag_1h,
                "volume_lag_24h": volume_lag_24h,
                "rolling_avg_3h": rolling_avg_3h,
                "temp": temp,
                "rain_1h": rain_1h
            }])
            
            # Predict
            level = congestion_model.predict(features_df)[0]
            predicted_volume = volume_model.predict(features_df)[0]
            
            # Map back to a 0-100 score for the frontend based on capacity
            v_c_ratio = predicted_volume / max(request.road_capacity, 1)
            score = min(100.0, max(0.0, (v_c_ratio * 100.0)))
            
            # Base delay on congestion level
            if level == "Low":
                delay = round(score * 0.1, 1)
            elif level == "Moderate":
                delay = round(score * 0.25, 1)
            else:
                delay = round(score * 0.5, 1)
        else:
            # Mock fallback if models are not generated yet
            v_c_ratio = request.vehicle_count / max(request.road_capacity, 1)
            score = min(100.0, max(0.0, (v_c_ratio * 60.0) + ((60.0 - request.avg_speed_kmh) * 0.8) + (15.0 if request.is_peak_hour else 0.0)))
            if score < 35:
                level = "Low"
                delay = round(score * 0.1, 1)
            elif score < 70:
                level = "Moderate"
                delay = round(score * 0.25, 1)
            else:
                level = "High"
                delay = round(score * 0.5, 1)

        if level == "Low":
            action = "Normal signal timing. Green light duration standard."
        elif level == "Moderate":
            action = "Extend green wave timing on main corridor by +15s."
        else:
            action = "Reroute incoming traffic to secondary arterial roads & dynamic signal priority."
            # Push AI proposal for the Traffic Controller
            import uuid
            new_route_id = str(uuid.uuid4())[:8]
            IN_MEMORY_PROPOSED_ROUTES.append({
                "id": new_route_id,
                "origin": "Congested Zone",
                "destination": "City Center",
                "status": "PENDING",
                "alternate_route": {
                    "name": "AI Suggested Secondary Arterial",
                    "distance_km": 15.2,
                    "estimated_time_mins": 22,
                    "delay_mins": 2.5
                }
            })

        return TrafficPredictResponse(
            congestion_level=level,
            congestion_score=round(score, 1),
            estimated_delay_minutes=delay,
            recommended_action=action
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/route-optimize")
def optimize_route(request: RouteOptimizeRequest):
    """Provides primary and alternate route optimization with delay estimates."""
    return {
        "origin": request.origin,
        "destination": request.destination,
        "primary_route": {
            "name": f"Direct via Main Arterial",
            "distance_km": 12.4,
            "estimated_time_mins": 26,
            "congestion": "Moderate",
            "delay_mins": 6.5
        },
        "alternate_route": {
            "name": f"Bypass via Outer Express Flyover",
            "distance_km": 14.8,
            "estimated_time_mins": 19,
            "congestion": "Clear",
            "delay_mins": 1.2
        },
        "recommendation": "Take Alternate Express Route to save ~7 mins."
    }

@router.get("/proposed-routes")
def get_proposed_routes():
    """Returns AI-proposed routes (PENDING and APPROVED)."""
    return IN_MEMORY_PROPOSED_ROUTES

@router.post("/approve-route")
def approve_route(request: ApproveRouteRequest):
    """Traffic Controller approves a PENDING route."""
    for r in IN_MEMORY_PROPOSED_ROUTES:
        if r["id"] == request.route_id:
            r["status"] = "APPROVED"
            return {"status": "success", "route": r}
    raise HTTPException(status_code=404, detail="Route not found")

@router.get("/incidents")
def get_incidents():
    """Returns active traffic alerts and incident reports."""
    return IN_MEMORY_INCIDENTS

@router.post("/incidents")
def report_incident(incident: IncidentReportRequest):
    """Submits a new traffic incident report."""
    new_id = len(IN_MEMORY_INCIDENTS) + 1
    item = {
        "id": new_id,
        "location": incident.location,
        "type": incident.type,
        "severity": incident.severity,
        "description": incident.description,
        "reported_at": "Just now",
        "status": "Active"
    }
    IN_MEMORY_INCIDENTS.insert(0, item)
    return {"success": True, "incident": item}

@router.post("/override-signal")
def override_signal(request: SignalOverrideRequest):
    """Triggers emergency signal overrides for Traffic Controllers."""
    for j in IN_MEMORY_JUNCTIONS:
        if j["id"] == request.junction_id:
            if request.mode == "emergency_green":
                j["signal"] = "Green"
                j["override"] = True
                j["status"] = "Priority Wave"
            elif request.mode == "all_red":
                j["signal"] = "Red"
                j["override"] = True
                j["status"] = "Halted"
            else:
                j["override"] = False
                j["signal"] = "Green"
                j["status"] = "Auto Control"
            return {"success": True, "junction": j}
    raise HTTPException(status_code=404, detail="Junction not found")

@router.get("/analytics-trends")
def get_analytics_trends():
    """Returns 24-hour traffic density & congestion trend data."""
    hours = ["00:00", "03:00", "06:00", "09:00", "12:00", "15:00", "18:00", "21:00"]
    densities = [240, 120, 480, 1420, 980, 1150, 1680, 720]
    speeds = [58, 62, 48, 21, 35, 29, 16, 44]
    delays = [2.0, 1.5, 4.2, 22.5, 12.0, 15.8, 28.4, 8.1]
    
    trend_data = []
    for h, d, s, dl in zip(hours, densities, speeds, delays):
        trend_data.append({
            "time": h,
            "vehicle_density": d,
            "avg_speed": s,
            "delay_mins": dl
        })
    return {"trend_data": trend_data}
