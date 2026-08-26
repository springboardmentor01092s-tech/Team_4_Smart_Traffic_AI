"""
test_models.py
---------------
Tests the three real-time-retrained models:
    - congestion_classifier.joblib  (Low / Moderate / High)
    - traffic_model.pkl             (volume regressor)
    - delay_regressor.joblib        (delay in minutes)

Two levels of testing:
  1. SANITY CHECK  -> load each model + run one prediction, confirm no crashes,
                       confirm output shape/type makes sense.
  2. HELD-OUT EVAL -> split traffic_data.csv into train/test, retrain-style features,
                       compute real accuracy / MAE on data the model hasn't "memorized".

Run from the backend/ directory:
    python scripts/test_models.py
"""

import json
import joblib
import pickle
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_absolute_error, classification_report

# ---- CONFIG: adjust these paths/columns to match your repo ----------------
ARTIFACTS_DIR = Path("app/ml/artifacts")
HOLDOUT_CSV = Path("data/true_holdout.csv")
REALTIME_CACHE = Path("data/realtime_traffic_fallback.json")

CONGESTION_MODEL = ARTIFACTS_DIR / "congestion_classifier.joblib"
VOLUME_MODEL = ARTIFACTS_DIR / "traffic_model.pkl"
DELAY_MODEL = ARTIFACTS_DIR / "delay_regressor.joblib"

# Union of all feature columns across both time-series volume and junction delay models
FEATURE_COLUMNS = [
    "hour", "day_of_week", "is_weekend", "volume_lag_1h", "volume_lag_24h", 
    "rolling_avg_3h", "temp", "rain_1h", "vehicle_count", "avg_speed_kmh", 
    "road_capacity", "is_peak_hour", "weather_code", "has_incident"
]
TARGET_CONGESTION = "congestion_level"
TARGET_VOLUME = "traffic_volume"
TARGET_DELAY = "delay_mins"


def load_model(path):
    if not path.exists():
        raise FileNotFoundError(f"Model not found: {path}")
    return joblib.load(path)



def sanity_check():
    print("=" * 60)
    print("STEP 1: SANITY CHECK — loading models & running one prediction")
    print("=" * 60)

    models = {}
    for name, path in [
        ("congestion_classifier", CONGESTION_MODEL),
        ("volume_regressor", VOLUME_MODEL),
        ("delay_regressor", DELAY_MODEL),
    ]:
        try:
            models[name] = load_model(path)
            print(f"[OK] Loaded {name} from {path}")
        except Exception as e:
            print(f"[FAIL] Could not load {name}: {e}")

    # Try to grab one real observation from the real-time cache as a live test row
    sample_row = None
    if REALTIME_CACHE.exists():
        try:
            with open(REALTIME_CACHE) as f:
                cache = json.load(f)
            if isinstance(cache, list) and len(cache) > 0:
                sample_row = cache[-1] # use the latest cached row
                print(f"\nUsing real-time sample observation for prediction test:\n{sample_row}")
        except Exception as e:
            print(f"[WARN] Could not parse real-time cache: {e}")

    if sample_row is None:
        print("\n[WARN] No real-time cache found — using manual sample row instead.")
        sample_row = {
            "hour": 17, "day_of_week": 2, "is_weekend": 0, "is_peak_hour": 1,
            "volume_lag_1h": 4200, "volume_lag_24h": 4100, "rolling_avg_3h": 4150,
            "temp": 22.5, "rain_1h": 0, "weather_code": 0, "road_capacity": 4000,
            "vehicle_count": 2100, "avg_speed_kmh": 45.0, "free_flow_speed_kmh": 60.0,
            "has_incident": 0
        }

    # Run predictions on the single row, extracting exact features required per model
    for name, model in models.items():
        try:
            # Check model feature names to avoid mismatch errors
            if hasattr(model, "feature_names_in_"):
                model_features = list(model.feature_names_in_)
            else:
                # Fallbacks if feature_names_in_ is not defined
                if name == "delay_regressor":
                    model_features = ["vehicle_count", "avg_speed_kmh", "road_capacity", "is_peak_hour", "weather_code", "has_incident"]
                else:
                    model_features = ["hour", "day_of_week", "is_weekend", "volume_lag_1h", "volume_lag_24h", "rolling_avg_3h", "temp", "rain_1h"]
            
            row_df = pd.DataFrame([{col: sample_row.get(col) for col in model_features}])
            pred = model.predict(row_df)[0]
            print(f"[OK] {name} prediction: {pred}")
        except Exception as e:
            print(f"[FAIL] {name} prediction errored: {e}")

    return models


def preprocess_data(df):
    """Applies preprocessing matching train_realtime_model.py to synthesize target and feature columns."""
    df["date_time"] = pd.to_datetime(df["date_time"])
    df["hour"] = df["date_time"].dt.hour
    df["day_of_week"] = df["date_time"].dt.dayofweek
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    
    if df["temp"].max() > 200:
        df["temp"] = df["temp"] - 273.15
        
    df["road_capacity"] = 4000
    df["vehicle_count"] = df["traffic_volume"]
    df["is_peak_hour"] = df["hour"].isin([7, 8, 9, 16, 17, 18]).astype(int)
    
    free_flow = 60.0
    speed_ratio = 1.0 - (df["vehicle_count"] / df["road_capacity"])
    df["avg_speed_kmh"] = free_flow * speed_ratio.clip(0.15, 0.95)
    df["free_flow_speed_kmh"] = free_flow
    
    np.random.seed(42)
    df["has_incident"] = np.where(df["avg_speed_kmh"] < 25.0, np.random.choice([0, 1], p=[0.7, 0.3], size=len(df)), 0)
    
    if "rain_1h" not in df.columns:
        df["rain_1h"] = 0.0
    df["rain_1h"] = (df["rain_1h"] > 0).astype(int)
    df["weather_code"] = df["rain_1h"]
    
    distance_km = 2.0
    df["delay_mins"] = (distance_km / df["avg_speed_kmh"] - distance_km / df["free_flow_speed_kmh"]) * 60.0
    df["delay_mins"] = df["delay_mins"].clip(lower=0.0)
    df["delay_mins"] += np.where(df["has_incident"] == 1, np.random.uniform(5.0, 15.0, size=len(df)), 0.0)
    
    conditions = [
        (df["avg_speed_kmh"] >= 45.0),
        (df["avg_speed_kmh"] >= 25.0) & (df["avg_speed_kmh"] < 45.0),
        (df["avg_speed_kmh"] < 25.0)
    ]
    choices = ["Low", "Moderate", "High"]
    df["congestion_level"] = np.select(conditions, choices, default="Low")
    
    # Sort and shift features
    df = df.sort_values("date_time").reset_index(drop=True)
    df["volume_lag_1h"] = df["traffic_volume"].shift(1)
    df["volume_lag_24h"] = df["traffic_volume"].shift(24)
    df["rolling_avg_3h"] = df["traffic_volume"].rolling(3).mean()
    df = df.dropna(subset=["volume_lag_1h", "volume_lag_24h", "rolling_avg_3h"]).reset_index(drop=True)
    
    return df


def held_out_evaluation():
    print("\n" + "=" * 60)
    print("STEP 2: HELD-OUT EVALUATION — real accuracy/MAE on unseen data")
    print("=" * 60)

    if not HOLDOUT_CSV.exists():
        print(f"[SKIP] Holdout CSV not found at {HOLDOUT_CSV}")
        return

    # Read preprocessed holdout split directly
    test_df = pd.read_csv(HOLDOUT_CSV)
    print(f"Loaded true holdout test split: {test_df.shape}")

    # --- Congestion classifier ---
    if CONGESTION_MODEL.exists() and TARGET_CONGESTION in test_df.columns:
        model = load_model(CONGESTION_MODEL)
        features = list(model.feature_names_in_)
        X_test = test_df[features]
        y_true = test_df[TARGET_CONGESTION]
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_true, y_pred)
        print(f"\nCongestion Classifier — True Holdout Accuracy: {acc:.2%}")
        print(classification_report(y_true, y_pred))

    # --- Volume regressor ---
    if VOLUME_MODEL.exists() and TARGET_VOLUME in test_df.columns:
        model = load_model(VOLUME_MODEL)
        features = list(model.feature_names_in_)
        X_test = test_df[features]
        y_true = test_df[TARGET_VOLUME]
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_true, y_pred)
        print(f"Volume Regressor — True Holdout MAE: {mae:.2f} vehicles/hr")

    # --- Delay regressor ---
    if DELAY_MODEL.exists() and TARGET_DELAY in test_df.columns:
        model = load_model(DELAY_MODEL)
        features = list(model.feature_names_in_)
        X_test = test_df[features]
        y_true = test_df[TARGET_DELAY]
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_true, y_pred)
        print(f"Delay Regressor — True Holdout MAE: {mae:.2f} minutes")


if __name__ == "__main__":
    sanity_check()
    held_out_evaluation()
    print("\nDone. Compare held-out numbers above against the *training* numbers "
          "from your walkthrough (MAE 129.84, Accuracy 98.05%, MAE 0.48). "
          "If held-out numbers are much worse, the model is overfitting.")
