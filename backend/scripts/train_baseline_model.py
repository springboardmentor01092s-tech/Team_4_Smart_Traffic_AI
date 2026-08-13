import pandas as pd
import numpy as np
import os
import joblib
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import mean_absolute_error, accuracy_score, classification_report, confusion_matrix

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "traffic_data.csv")
ARTIFACTS_DIR = os.path.join(BASE_DIR, "app", "ml", "artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

def load_and_preprocess_real_data():
    """Loads and feature-engineers the real UCI Metro Interstate Traffic Volume dataset."""
    print(f"Loading real dataset from {DATA_PATH}...")
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Dataset not found at {DATA_PATH}. Run download_dataset.py first.")
        
    df = pd.read_csv(DATA_PATH, parse_dates=["date_time"])
    
    # Sort by time to ensure time-series lag ordering
    df = df.sort_values("date_time").drop_duplicates(subset=["date_time"]).reset_index(drop=True)
    
    # Feature extraction from timestamp
    df["hour"] = df["date_time"].dt.hour
    df["day_of_week"] = df["date_time"].dt.dayofweek
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    
    # Convert Kelvin to Celsius if applicable
    if df["temp"].max() > 200:
        df["temp"] = df["temp"] - 273.15
        
    # Weather flag
    if "rain_1h" not in df.columns:
        df["rain_1h"] = 0.0
    df["rain_1h"] = (df["rain_1h"] > 0).astype(int)
    
    # Lag & Rolling Features (The key time-series drivers)
    df["volume_lag_1h"] = df["traffic_volume"].shift(1)
    df["volume_lag_24h"] = df["traffic_volume"].shift(24)
    df["rolling_avg_3h"] = df["traffic_volume"].rolling(3).mean()
    
    # Clean rows with missing lag values
    df = df.dropna(subset=["volume_lag_1h", "volume_lag_24h", "rolling_avg_3h"]).reset_index(drop=True)
    
    # Bucket Congestion Level for classification
    # For Metro Interstate: High > 4500, Moderate 2500-4500, Low < 2500
    conditions = [
        (df["traffic_volume"] < 2500),
        (df["traffic_volume"] >= 2500) & (df["traffic_volume"] < 4500),
        (df["traffic_volume"] >= 4500)
    ]
    choices = ["Low", "Moderate", "High"]
    df["congestion_level"] = np.select(conditions, choices, default="Low")
    
    return df

def train_baseline():
    df = load_and_preprocess_real_data()
    print(f"Cleaned dataset shape: {df.shape}")
    
    features = ["hour", "day_of_week", "is_weekend", "volume_lag_1h", "volume_lag_24h", "rolling_avg_3h", "temp", "rain_1h"]
    X = df[features]
    y_reg = df["traffic_volume"]
    y_clf = df["congestion_level"]
    
    # Split by time (80% train, 20% test)
    split_idx = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_reg_train, y_reg_test = y_reg.iloc[:split_idx], y_reg.iloc[split_idx:]
    y_clf_train, y_clf_test = y_clf.iloc[:split_idx], y_clf.iloc[split_idx:]
    
    print("\n--- Training RandomForest Regressor on Real Dataset ---")
    regressor = RandomForestRegressor(n_estimators=150, max_depth=12, random_state=42, n_jobs=-1)
    regressor.fit(X_train, y_reg_train)
    reg_preds = regressor.predict(X_test)
    mae = mean_absolute_error(y_reg_test, reg_preds)
    
    # Floor filter for MAPE to avoid division by near-zero overnight volume counts (<100 vehicles/hr)
    valid_mask = y_reg_test >= 100
    mape = (np.abs(y_reg_test[valid_mask] - reg_preds[valid_mask]) / y_reg_test[valid_mask]).mean() * 100
    print(f"RandomForest Volume Regressor MAE: {mae:.2f} vehicles/hr")
    print(f"RandomForest Volume Regressor MAPE (volume >= 100): {mape:.2f}%")
    
    print("\n--- Training RandomForest Classifier on Real Dataset ---")
    classifier = RandomForestClassifier(n_estimators=150, max_depth=12, random_state=42, n_jobs=-1)
    classifier.fit(X_train, y_clf_train)
    clf_preds = classifier.predict(X_test)
    accuracy = accuracy_score(y_clf_test, clf_preds)
    labels = ["Low", "Moderate", "High"]
    clf_report = classification_report(y_clf_test, clf_preds, labels=labels, target_names=labels)
    conf_mat = confusion_matrix(y_clf_test, clf_preds, labels=labels)
    
    print(f"RandomForest Congestion Classifier Accuracy: {accuracy:.2%}")
    print("\nClassification Report:\n", clf_report)
    print("Confusion Matrix (Low, Moderate, High):\n", conf_mat)
    
    # Save Artifacts
    reg_path = os.path.join(ARTIFACTS_DIR, "traffic_model.pkl")
    clf_path = os.path.join(ARTIFACTS_DIR, "congestion_classifier.joblib")
    metrics_path = os.path.join(ARTIFACTS_DIR, "baseline_metrics.txt")
    
    joblib.dump(regressor, reg_path)
    joblib.dump(classifier, clf_path)
    
    with open(metrics_path, "w") as f:
        f.write(f"RandomForest Regressor MAE: {mae:.2f} vehicles/hr\n")
        f.write(f"RandomForest Regressor MAPE (volume >= 100): {mape:.2f}%\n")
        f.write(f"RandomForest Classifier Accuracy: {accuracy:.4f}\n\n")
        f.write("Classification Report:\n" + clf_report + "\n")
        f.write("Confusion Matrix (Rows=True, Cols=Pred) [Low, Moderate, High]:\n")
        f.write(str(conf_mat) + "\n")
        
    print(f"\nModels and detailed metrics successfully saved to {ARTIFACTS_DIR}")
    return mae, accuracy

if __name__ == "__main__":
    train_baseline()
