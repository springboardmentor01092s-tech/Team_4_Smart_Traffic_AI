import sys
import os
import pandas as pd
import numpy as np
import joblib
import json
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import mean_absolute_error, accuracy_score

# Ensure backend directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.mongodb import connect_to_mongo, get_mongo_db, close_mongo_connection

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACTS_DIR = os.path.join(BASE_DIR, "app", "ml", "artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

FALLBACK_FILE_PATH = os.path.join(BASE_DIR, "data", "realtime_traffic_fallback.json")
HOLDOUT_CSV_PATH = os.path.join(BASE_DIR, "data", "true_holdout.csv")

def load_data_from_mongo_or_fallback():
    """Loads traffic observations from MongoDB or fallback local JSON storage. Falls back to CSV bootstrap if empty."""
    records = []
    
    # 1. Try MongoDB
    connect_to_mongo()
    db = get_mongo_db()
    if db is not None:
        try:
            collection = db["realtime_traffic"]
            cursor = collection.find({}).sort("timestamp", 1)
            records = list(cursor)
            print(f"Retrieved {len(records)} real-time records from MongoDB.")
        except Exception as e:
            print(f"Error querying MongoDB: {e}")
    close_mongo_connection()
    
    # 2. Try Local Fallback JSON
    if len(records) == 0 and os.path.exists(FALLBACK_FILE_PATH):
        try:
            print(f"Checking fallback local cache file at {FALLBACK_FILE_PATH}...")
            with open(FALLBACK_FILE_PATH, "r") as f:
                records = json.load(f)
                print(f"Loaded {len(records)} real-time records from local fallback cache.")
        except Exception as e:
            print(f"Error loading local fallback file: {e}")
            records = []
            
    # 3. If still empty or insufficient (< 100), bootstrap/augment with the baseline dataset
    if len(records) < 100:
        print("Insufficient real-time data (< 100 records). Bootstrapping dataset using baseline traffic data...")
        csv_path = os.path.join(BASE_DIR, "data", "traffic_data.csv")
        if not os.path.exists(csv_path):
            csv_path = os.path.join(ARTIFACTS_DIR, "historical_traffic.csv")
            
        if os.path.exists(csv_path):
            print(f"Loading seed data from {csv_path}...")
            df_seed = pd.read_csv(csv_path)
            
            # Format date features
            if "date_time" in df_seed.columns:
                df_seed["date_time"] = pd.to_datetime(df_seed["date_time"])
                df_seed["hour"] = df_seed["date_time"].dt.hour
                df_seed["day_of_week"] = df_seed["date_time"].dt.dayofweek
                df_seed["is_weekend"] = df_seed["day_of_week"].isin([5, 6]).astype(int)
            
            if "temp" in df_seed.columns and df_seed["temp"].max() > 200:
                df_seed["temp"] = df_seed["temp"] - 273.15
                
            # Synthesize real-time variables for bootstrap
            df_seed["road_capacity"] = 4000
            df_seed["vehicle_count"] = df_seed["traffic_volume"]
            df_seed["is_peak_hour"] = df_seed["hour"].isin([7, 8, 9, 16, 17, 18]).astype(int)
            
            # Estimate speed drop: Speed = FreeFlow * (1 - volume / capacity)
            free_flow = 60.0
            speed_ratio = 1.0 - (df_seed["vehicle_count"] / df_seed["road_capacity"])
            df_seed["avg_speed_kmh"] = free_flow * speed_ratio.clip(0.15, 0.95)
            df_seed["free_flow_speed_kmh"] = free_flow
            
            df_seed["has_incident"] = np.where(df_seed["avg_speed_kmh"] < 25.0, np.random.choice([0, 1], p=[0.7, 0.3], size=len(df_seed)), 0)
            
            if "rain_1h" not in df_seed.columns:
                df_seed["rain_1h"] = 0.0
            df_seed["rain_1h"] = (df_seed["rain_1h"] > 0).astype(int)
            df_seed["weather_code"] = df_seed["rain_1h"]
            
            # Target delay calculation
            distance_km = 2.0
            df_seed["delay_mins"] = (distance_km / df_seed["avg_speed_kmh"] - distance_km / df_seed["free_flow_speed_kmh"]) * 60.0
            df_seed["delay_mins"] = df_seed["delay_mins"].clip(lower=0.0)
            df_seed["delay_mins"] += np.where(df_seed["has_incident"] == 1, np.random.uniform(5.0, 15.0, size=len(df_seed)), 0.0)
            
            # Target congestion level
            conditions = [
                (df_seed["avg_speed_kmh"] >= 45.0),
                (df_seed["avg_speed_kmh"] >= 25.0) & (df_seed["avg_speed_kmh"] < 45.0),
                (df_seed["avg_speed_kmh"] < 25.0)
            ]
            choices = ["Low", "Moderate", "High"]
            df_seed["congestion_level"] = np.select(conditions, choices, default="Low")
            
            # Time-series shift features
            df_seed = df_seed.sort_values("date_time").reset_index(drop=True)
            df_seed["volume_lag_1h"] = df_seed["traffic_volume"].shift(1)
            df_seed["volume_lag_24h"] = df_seed["traffic_volume"].shift(24)
            df_seed["rolling_avg_3h"] = df_seed["traffic_volume"].rolling(3).mean()
            df_seed = df_seed.dropna(subset=["volume_lag_1h", "volume_lag_24h", "rolling_avg_3h"]).reset_index(drop=True)
            
            return df_seed
        else:
            raise FileNotFoundError("Could not find seed CSV datasets to bootstrap training. Run download_dataset.py first.")
            
    # If we loaded from MongoDB or fallback cache
    df = pd.DataFrame(records)
    
    # Parse timestamp strings
    df["parsed_time"] = pd.to_datetime(df["timestamp"])
    
    # Calculate target variables
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
    
    df["traffic_volume"] = df["vehicle_count"]
    
    # Generate lag features
    df = df.sort_values("parsed_time").reset_index(drop=True)
    df["volume_lag_1h"] = df["traffic_volume"].shift(1)
    df["volume_lag_24h"] = df["traffic_volume"].shift(24)
    df["rolling_avg_3h"] = df["traffic_volume"].rolling(3).mean()
    
    # Backfill lag features
    df["volume_lag_1h"] = df["volume_lag_1h"].bfill().ffill()
    df["volume_lag_24h"] = df["volume_lag_24h"].bfill().ffill()
    df["rolling_avg_3h"] = df["rolling_avg_3h"].bfill().ffill()
    
    return df

def retrain_all_models():
    df_all = load_data_from_mongo_or_fallback()
    print(f"Data shape loaded: {df_all.shape}")
    
    # Methodology Fix: split the dataset into train and holdout BEFORE training.
    # 85% train, 15% true holdout.
    df, df_holdout = train_test_split(df_all, test_size=0.15, random_state=42)
    print(f"Split data: Training Set = {df.shape[0]} samples, Holdout Set = {df_holdout.shape[0]} samples")
    
    # Save the holdout set for honest test evaluation
    df_holdout.to_csv(HOLDOUT_CSV_PATH, index=False)
    print(f"Saved true holdout split to {HOLDOUT_CSV_PATH}")
    
    # 1. Train Volume Regressor (traffic_model.pkl)
    time_features = ["hour", "day_of_week", "is_weekend", "volume_lag_1h", "volume_lag_24h", "rolling_avg_3h", "temp", "rain_1h"]
    X_vol = df[time_features]
    y_vol = df["traffic_volume"]
    
    print("\n--- Training Real-Time Volume Regressor (traffic_model.pkl) ---")
    vol_regressor = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    vol_regressor.fit(X_vol, y_vol)
    vol_preds = vol_regressor.predict(X_vol)
    vol_mae = mean_absolute_error(y_vol, vol_preds)
    print(f"Volume Regressor Training MAE: {vol_mae:.2f} vehicles/hr")
    
    # 2. Train Congestion Classifier (congestion_classifier.joblib)
    y_clf = df["congestion_level"]
    print("\n--- Training Real-Time Congestion Classifier (congestion_classifier.joblib) ---")
    classifier = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    classifier.fit(X_vol, y_clf)
    clf_preds = classifier.predict(X_vol)
    clf_accuracy = accuracy_score(y_clf, clf_preds)
    print(f"Congestion Classifier Training Accuracy: {clf_accuracy:.2%}")
    
    # 3. Train Delay Regressor (delay_regressor.joblib)
    delay_features = ["vehicle_count", "avg_speed_kmh", "road_capacity", "is_peak_hour", "weather_code", "has_incident"]
    X_delay = df[delay_features]
    y_delay = df["delay_mins"]
    
    print("\n--- Training Real-Time Delay Regressor (delay_regressor.joblib) ---")
    delay_regressor = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42, n_jobs=-1)
    delay_regressor.fit(X_delay, y_delay)
    delay_preds = delay_regressor.predict(X_delay)
    delay_mae = mean_absolute_error(y_delay, delay_preds)
    print(f"Delay Regressor Training MAE: {delay_mae:.2f} minutes")
    
    # Save the updated model artifacts
    vol_path = os.path.join(ARTIFACTS_DIR, "traffic_model.pkl")
    clf_path = os.path.join(ARTIFACTS_DIR, "congestion_classifier.joblib")
    delay_path = os.path.join(ARTIFACTS_DIR, "delay_regressor.joblib")
    
    joblib.dump(vol_regressor, vol_path)
    joblib.dump(classifier, clf_path)
    joblib.dump(delay_regressor, delay_path)
    
    # Update metrics file
    metrics_path = os.path.join(ARTIFACTS_DIR, "realtime_metrics.txt")
    with open(metrics_path, "w") as f:
        f.write("=== REAL-TIME MODEL RETRAINING METRICS ===\n")
        f.write(f"Retrained At: {pd.Timestamp.now().isoformat()}\n")
        f.write(f"Dataset Size: {len(df)} rows\n")
        f.write(f"Volume Regressor Training MAE: {vol_mae:.2f} vehicles/hr\n")
        f.write(f"Congestion Classifier Training Accuracy: {clf_accuracy:.4f}\n")
        f.write(f"Delay Regressor Training MAE: {delay_mae:.2f} minutes\n")
        
    print(f"\nAll models retrained successfully and saved to {ARTIFACTS_DIR}!")

if __name__ == "__main__":
    retrain_all_models()
