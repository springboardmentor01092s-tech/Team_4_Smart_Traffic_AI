"""
pipeline_service.py
Orchestrates: collect -> predict -> alert -> store -> broadcast, on a schedule.
"""
import os
import json
import random
import logging
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from app.core.mongodb import get_mongo_db
from app.services.tomtom_service import TomTomService
from app.services.here_service import HEREService
from app.services import alert_service, notification_service
from app.services.analytics_service import JUNCTION_COORDS, FALLBACK_TRAFFIC_PATH

logger = logging.getLogger(__name__)

# Predefined junctions list matching collect_realtime_data.py
TARGET_JUNCTIONS = [
    {"id": "J1", "name": "Central Plaza Crossing", "lat": 12.9716, "lon": 77.5946, "bbox": "77.5900,12.9700,77.6000,12.9800", "road_capacity": 4000},
    {"id": "J2", "name": "MG Road & 5th Avenue", "lat": 12.9735, "lon": 77.6010, "bbox": "77.5950,12.9700,77.6050,12.9800", "road_capacity": 3800},
    {"id": "J3", "name": "Tech Corridor Junction", "lat": 12.9592, "lon": 77.6974, "bbox": "77.6900,12.9500,77.7050,12.9650", "road_capacity": 4500},
    {"id": "J4", "name": "Airport Expressway Flyover", "lat": 13.1986, "lon": 77.7066, "bbox": "77.7000,13.1900,77.7150,13.2050", "road_capacity": 6000},
    {"id": "J5", "name": "Metro Station Interchange", "lat": 12.9815, "lon": 77.5951, "bbox": "77.5900,12.9750,77.6000,12.9850", "road_capacity": 3500},
    {"id": "J6", "name": "South Port Boulevard", "lat": 12.9433, "lon": 77.6205, "bbox": "77.6150,12.9380,77.6250,12.9480", "road_capacity": 3200}
]

_models_cache = {}

def get_pipeline_models():
    """Loads and caches all three RandomForest ML models."""
    if not _models_cache:
        # Load path-resolver helper from app.ml.congestion
        from app.ml.congestion import _resolve_artifact_path
        
        clf_path = _resolve_artifact_path("congestion_classifier.joblib")
        vol_path = _resolve_artifact_path("traffic_model.pkl")
        delay_path = _resolve_artifact_path("delay_regressor.joblib")
        
        logger.info("Initializing models for serving pipeline...")
        _models_cache["congestion"] = joblib.load(clf_path)
        _models_cache["volume"] = joblib.load(vol_path)
        _models_cache["delay"] = joblib.load(delay_path)
        
        # Ensure single-thread prediction for speed optimization
        for m in _models_cache.values():
            if hasattr(m, "set_params"):
                m.set_params(n_jobs=1)
                
    return _models_cache["congestion"], _models_cache["volume"], _models_cache["delay"]

def fetch_lag_features(junction_id: str, current_volume: float) -> tuple[float, float, float]:
    """Queries MongoDB history or local fallback cache to resolve volume lag features."""
    db = get_mongo_db()
    if db is not None:
        try:
            # Query last 30 observations for this junction to compute lags
            cursor = db.realtime_traffic.find(
                {"junction_id": junction_id}
            ).sort("timestamp", -1).limit(30)
            history = list(cursor)
            
            volumes = [h.get("vehicle_count", current_volume) for h in history]
            
            volume_lag_1h = volumes[0] if len(volumes) > 0 else current_volume
            volume_lag_24h = volumes[23] if len(volumes) > 23 else current_volume
            rolling_avg_3h = sum(volumes[:3]) / len(volumes[:3]) if len(volumes) > 0 else current_volume
            
            return float(volume_lag_1h), float(volume_lag_24h), float(rolling_avg_3h)
        except Exception as e:
            logger.warning(f"Failed to query lag features from MongoDB: {e}")
            
    # Try local cache
    if FALLBACK_TRAFFIC_PATH.exists():
        try:
            with open(FALLBACK_TRAFFIC_PATH, "r") as f:
                records = json.load(f)
            # Filter and sort
            history = [r for r in records if r.get("junction_id") == junction_id]
            history = sorted(history, key=lambda x: x.get("timestamp", ""), reverse=True)
            
            volumes = [h.get("vehicle_count", current_volume) for h in history]
            
            volume_lag_1h = volumes[0] if len(volumes) > 0 else current_volume
            volume_lag_24h = volumes[23] if len(volumes) > 23 else current_volume
            rolling_avg_3h = sum(volumes[:3]) / len(volumes[:3]) if len(volumes) > 0 else current_volume
            
            return float(volume_lag_1h), float(volume_lag_24h), float(rolling_avg_3h)
        except Exception as e:
            logger.error(f"Failed to query lag features from local fallback: {e}")
            
    # Safe mathematical approximation fallback
    volume_lag_1h = max(0.0, current_volume + np.random.normal(0, 20))
    volume_lag_24h = max(0.0, current_volume + np.random.normal(0, 50))
    rolling_avg_3h = float(current_volume)
    return volume_lag_1h, volume_lag_24h, rolling_avg_3h

def save_observation(obs: dict):
    """Saves observation record to MongoDB or falls back to local JSON cache."""
    obs_to_save = obs.copy()
    
    # Standardize datetime to string representation for local JSON storage consistency
    if isinstance(obs_to_save.get("timestamp"), datetime):
        obs_to_save["timestamp"] = obs_to_save["timestamp"].isoformat()
        
    db = get_mongo_db()
    if db is not None:
        try:
            db.realtime_traffic.insert_one(obs_to_save)
            return
        except Exception as e:
            logger.warning(f"MongoDB write failed for observation: {e}. Storing locally.")
            obs_to_save.pop("_id", None)
            
    # Append locally
    try:
        existing = []
        if FALLBACK_TRAFFIC_PATH.exists():
            with open(FALLBACK_TRAFFIC_PATH, "r") as f:
                try:
                    existing = json.load(f)
                except Exception:
                    existing = []
        existing.append(obs_to_save)
        with open(FALLBACK_TRAFFIC_PATH, "w") as f:
            json.dump(existing, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to append local fallback traffic observation: {e}")

async def run_pipeline_cycle():
    """Runs a single workflow cycle: collect raw data -> predict metrics -> generate & save alerts -> broadcast."""
    logger.info("Executing periodic traffic pipeline cycle...")
    
    # Load ML models
    try:
        congestion_model, volume_model, delay_model = get_pipeline_models()
    except Exception as e:
        logger.error(f"Failed to load pipeline models: {e}. Aborting cycle.")
        return
        
    tomtom = TomTomService()
    here = HEREService()
    
    now = datetime.now(timezone.utc)
    hour = now.hour
    day_of_week = now.weekday()
    is_weekend = 1 if day_of_week >= 5 else 0
    is_peak = 1 if hour in [7, 8, 9, 16, 17, 18] else 0
    
    for j in TARGET_JUNCTIONS:
        try:
            # 1. Fetch raw real-time traffic data from APIs
            tt_flow = tomtom.get_flow_data(j["lat"], j["lon"])
            here_flow = here.get_flow_data(j["bbox"])
            tt_incidents = tomtom.get_incidents(j["bbox"])
            
            # 2. Preprocess / Extract speeds
            tt_data = tt_flow.get("flowSegmentData", {})
            tt_speed = tt_data.get("currentSpeed", 45)
            tt_free_speed = tt_data.get("freeFlowSpeed", 60)
            
            here_speed = 45.0
            here_jam = 0.0
            results = here_flow.get("results", [])
            if results:
                flow_info = results[0].get("currentFlow", {})
                here_speed = flow_info.get("speed", 45.0)
                here_jam = flow_info.get("jamFactor", 0.0)
                
            avg_speed = float((tt_speed + here_speed) / 2.0)
            free_flow_speed = float(tt_free_speed)
            
            # 3. Estimate density metrics & current volume
            speed_ratio = min(1.0, max(0.1, avg_speed / free_flow_speed))
            estimated_density = 1.0 - speed_ratio
            base_vol = j["road_capacity"] * estimated_density
            vehicle_count = int(max(150, min(j["road_capacity"], base_vol + random.normalvariate(0, 100))))
            
            if is_peak and vehicle_count < (j["road_capacity"] * 0.4):
                vehicle_count = int(j["road_capacity"] * random.uniform(0.4, 0.85))
                
            has_incident = 1 if (len(tt_incidents) > 0 or here_jam > 7.0) else 0
            
            # Weather approximations
            temp = 24.5 + random.uniform(-2, 2)
            rain_1h = 1 if (has_incident and random.random() > 0.8) else 0
            weather_code = 1 if rain_1h else 0
            
            # 4. Fetch dynamic lag features
            volume_lag_1h, volume_lag_24h, rolling_avg_3h = fetch_lag_features(j["id"], float(vehicle_count))
            
            # 5. Build feature rows and predict
            # Time-series volume model features
            features_vol_list = ["hour", "day_of_week", "is_weekend", "volume_lag_1h", "volume_lag_24h", "rolling_avg_3h", "temp", "rain_1h"]
            features_vol_df = pd.DataFrame([{
                "hour": hour,
                "day_of_week": day_of_week,
                "is_weekend": is_weekend,
                "volume_lag_1h": volume_lag_1h,
                "volume_lag_24h": volume_lag_24h,
                "rolling_avg_3h": rolling_avg_3h,
                "temp": temp,
                "rain_1h": rain_1h
            }])[features_vol_list]
            
            # Predict Volume and Congestion level
            predicted_volume = float(volume_model.predict(features_vol_df)[0])
            congestion_level = str(congestion_model.predict(features_vol_df)[0])
            
            # Delay model features
            features_delay_list = ["vehicle_count", "avg_speed_kmh", "road_capacity", "is_peak_hour", "weather_code", "has_incident"]
            features_delay_df = pd.DataFrame([{
                "vehicle_count": vehicle_count,
                "avg_speed_kmh": avg_speed,
                "road_capacity": j["road_capacity"],
                "is_peak_hour": is_peak,
                "weather_code": weather_code,
                "has_incident": has_incident
            }])[features_delay_list]
            
            # Predict Delay
            predicted_delay = float(delay_model.predict(features_delay_df)[0])

            
            # 6. Compose and save observation
            observation = {
                "junction_id": j["id"],
                "junction_name": j["name"],
                "timestamp": now,
                "hour": hour,
                "day_of_week": day_of_week,
                "is_weekend": is_weekend,
                "is_peak_hour": is_peak,
                "road_capacity": j["road_capacity"],
                "avg_speed_kmh": round(avg_speed, 2),
                "free_flow_speed_kmh": round(free_flow_speed, 2),
                "vehicle_count": int(predicted_volume),
                "has_incident": has_incident,
                "temp": round(temp, 1),
                "rain_1h": rain_1h,
                "weather_code": weather_code,
                "predicted_delay_mins": round(predicted_delay, 2),
                "congestion_level": congestion_level,
                "meta": {
                    "source": "Serving Pipeline",
                    "processed_at": now.strftime("%Y-%m-%d %H:%M:%S")
                }
            }
            save_observation(observation)
            
            # 7. Evaluate and trigger alerts
            congestion_alert = alert_service.evaluate_congestion_alert(
                j["id"], congestion_level, predicted_volume, predicted_delay
            )
            accident_alerts = alert_service.evaluate_accident_alerts(j["id"], tt_incidents)
            
            # Save and broadcast alerts in real-time
            all_triggered_alerts = [congestion_alert] + accident_alerts
            for alert in filter(None, all_triggered_alerts):
                notification_service.save_alert(alert)
                await notification_service.broadcast_alert(alert)
                logger.info(f"Triggered Alert: {alert['message']}")
                
        except Exception as e:
            logger.error(f"Error in pipeline cycle for junction {j['id']}: {e}")
            
    logger.info("Traffic pipeline cycle execution completed.")
