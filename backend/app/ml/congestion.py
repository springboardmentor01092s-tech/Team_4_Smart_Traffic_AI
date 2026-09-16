import os
import joblib
import pandas as pd

# Path resolution: find artifacts directory reliably
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ML_DIR = os.path.dirname(os.path.abspath(__file__))

def _resolve_artifact_path(filename: str) -> str:
    candidates = [
        os.path.join(_ML_DIR, "artifacts", filename),
        os.path.join(BASE_DIR, "artifacts", filename),
        os.path.join(BASE_DIR, "ml", "artifacts", filename),
        os.path.join(BASE_DIR, "app", "ml", "artifacts", filename),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    # Default to standard path relative to ML module
    return os.path.join(_ML_DIR, "artifacts", filename)

CONGESTION_MODEL_PATH = _resolve_artifact_path("congestion_classifier.joblib")
DELAY_MODEL_PATH = _resolve_artifact_path("delay_regressor.joblib")

_model_cache = {}


def load_models():
    """Loads congestion classifier and delay regressor joblib models."""
    if "congestion_model" not in _model_cache:
        _model_cache["congestion_model"] = joblib.load(CONGESTION_MODEL_PATH)
    if "delay_model" not in _model_cache:
        _model_cache["delay_model"] = joblib.load(DELAY_MODEL_PATH)

    return _model_cache["congestion_model"], _model_cache["delay_model"]


def prepare_congestion_features(
    hour,
    day_of_week,
    volume_lag_1h,
    volume_lag_24h,
    rolling_avg_3h,
    temp,
    rain_1h
):
    is_weekend = 1 if day_of_week >= 5 else 0

    return pd.DataFrame([{
        "hour": hour,
        "day_of_week": day_of_week,
        "is_weekend": is_weekend,
        "volume_lag_1h": volume_lag_1h,
        "volume_lag_24h": volume_lag_24h,
        "rolling_avg_3h": rolling_avg_3h,
        "temp": temp,
        "rain_1h": rain_1h
    }])


def forecast_congestion(
    hour,
    day_of_week,
    volume_lag_1h,
    volume_lag_24h,
    rolling_avg_3h,
    temp,
    rain_1h
):
    congestion_model, _ = load_models()

    features = prepare_congestion_features(
        hour,
        day_of_week,
        volume_lag_1h,
        volume_lag_24h,
        rolling_avg_3h,
        temp,
        rain_1h
    )

    prediction = congestion_model.predict(features)[0]

    return str(prediction)


def forecast_delay(
    vehicle_count,
    avg_speed_kmh,
    road_capacity,
    is_peak_hour,
    weather_code,
    has_incident
):
    _, delay_model = load_models()

    features = pd.DataFrame([{
        "vehicle_count": vehicle_count,
        "avg_speed_kmh": avg_speed_kmh,
        "road_capacity": road_capacity,
        "is_peak_hour": is_peak_hour,
        "weather_code": weather_code,
        "has_incident": has_incident
    }])

    prediction = delay_model.predict(features)[0]

    return round(float(prediction), 2)


def generate_forecast(
    hour,
    day_of_week,
    volume_lag_1h,
    volume_lag_24h,
    rolling_avg_3h,
    temp,
    rain_1h,
    vehicle_count,
    avg_speed_kmh,
    road_capacity,
    is_peak_hour,
    weather_code,
    has_incident
):
    congestion = forecast_congestion(
        hour,
        day_of_week,
        volume_lag_1h,
        volume_lag_24h,
        rolling_avg_3h,
        temp,
        rain_1h
    )

    delay = forecast_delay(
        vehicle_count,
        avg_speed_kmh,
        road_capacity,
        is_peak_hour,
        weather_code,
        has_incident
    )

    return {
        "forecast": {
            "congestion_level": congestion,
            "predicted_delay_minutes": delay
        },
        "traffic_conditions": {
            "vehicle_count": vehicle_count,
            "average_speed_kmh": avg_speed_kmh,
            "road_capacity": road_capacity,
            "is_peak_hour": bool(is_peak_hour),
            "weather_code": weather_code,
            "has_incident": bool(has_incident)
        },
        "forecast_context": {
            "hour": hour,
            "day_of_week": day_of_week,
            "temperature": temp,
            "rain_1h": rain_1h
        }
    }
