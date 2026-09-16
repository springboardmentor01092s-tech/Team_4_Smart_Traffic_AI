import pandas as pd
import numpy as np
import os
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "traffic_data.csv")
ARTIFACTS_DIR = os.path.join(BASE_DIR, "app", "ml", "artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

def load_and_prepare_multivariate_lstm_data(window_size=12):
    """Loads real dataset and prepares multi-channel sequence arrays for LSTM."""
    print(f"Loading real dataset for Multivariate LSTM from {DATA_PATH}...")
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Dataset not found at {DATA_PATH}. Run download_dataset.py first.")
        
    df = pd.read_csv(DATA_PATH, parse_dates=["date_time"])
    df = df.sort_values("date_time").drop_duplicates(subset=["date_time"]).reset_index(drop=True)
    
    # Feature Engineering matching baseline
    df["hour"] = df["date_time"].dt.hour
    df["day_of_week"] = df["date_time"].dt.dayofweek
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    
    if df["temp"].max() > 200:
        df["temp"] = df["temp"] - 273.15
        
    if "rain_1h" not in df.columns:
        df["rain_1h"] = 0.0
    df["rain_1h"] = (df["rain_1h"] > 0).astype(int)
    
    # Multivariate Channels: Target is traffic_volume (index 0)
    feature_cols = ["traffic_volume", "hour", "day_of_week", "is_weekend", "temp", "rain_1h"]
    data_features = df[feature_cols].values.astype(np.float32)
    
    # Scale features across all channels
    scaler = MinMaxScaler()
    scaled_features = scaler.fit_transform(data_features)
    
    X, y = [], []
    for i in range(len(scaled_features) - window_size):
        X.append(scaled_features[i : i + window_size, :]) # Shape: (window_size, n_features)
        y.append(scaled_features[i + window_size, 0])      # Target: traffic_volume (col index 0)
        
    X = np.array(X) # (samples, window_size, n_features)
    y = np.array(y)
    
    # 80/20 train/test split
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    return X_train, X_test, y_train, y_test, scaler, df["traffic_volume"].values[split_idx + window_size:]

def train_lstm():
    window_size = 12
    X_train, X_test, y_train, y_test, scaler, actual_raw_y_test = load_and_prepare_multivariate_lstm_data(window_size=window_size)
    n_features = X_train.shape[2]
    print(f"Multivariate Input Shape: X_train={X_train.shape} ({n_features} channels)")
    
    print("\n--- Training Multivariate TensorFlow LSTM Model ---")
    model = tf.keras.Sequential([
        tf.keras.layers.LSTM(64, input_shape=(window_size, n_features), return_sequences=False),
        tf.keras.layers.Dropout(0.1),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dense(1)
    ])
    
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), loss="mae")
    
    # Train model
    history = model.fit(
        X_train, y_train,
        epochs=15,
        batch_size=64,
        validation_split=0.1,
        verbose=1
    )
    
    # Predict and inverse scale
    scaled_preds = model.predict(X_test).flatten()
    
    # Inverse scaling for volume target (col index 0)
    vol_min = scaler.data_min_[0]
    vol_max = scaler.data_max_[0]
    preds = scaled_preds * (vol_max - vol_min) + vol_min
    actuals = actual_raw_y_test[:len(preds)]
    
    mae = mean_absolute_error(actuals, preds)
    valid_mask = actuals >= 100
    mape = (np.abs(actuals[valid_mask] - preds[valid_mask]) / actuals[valid_mask]).mean() * 100
    
    print(f"\nMultivariate TensorFlow LSTM Volume Regressor MAE: {mae:.2f} vehicles/hr")
    print(f"Multivariate TensorFlow LSTM Volume Regressor MAPE (volume >= 100): {mape:.2f}%")
    
    # Compare with Baseline
    baseline_metrics_path = os.path.join(ARTIFACTS_DIR, "baseline_metrics.txt")
    rf_mae, rf_mape = None, None
    if os.path.exists(baseline_metrics_path):
        with open(baseline_metrics_path, "r") as f:
            for line in f:
                if "RandomForest Regressor MAE:" in line:
                    rf_mae = float(line.split(":")[-1].replace("vehicles/hr", "").strip())
                if "RandomForest Regressor MAPE:" in line:
                    rf_mape = float(line.split(":")[-1].replace("%", "").strip())
                    
    print("\n================ ML vs Deep Learning Benchmark ================")
    print(f"RandomForest Regressor (Tabular ML)   : MAE = {rf_mae if rf_mae else 'N/A'} vehicles/hr | MAPE = {rf_mape if rf_mape else 'N/A'}%")
    print(f"Multivariate Keras LSTM (Deep Learning): MAE = {mae:.2f} vehicles/hr | MAPE = {mape:.2f}%")
    print("================================================================")
    
    # Save Model & Metrics
    model_path = os.path.join(ARTIFACTS_DIR, "traffic_lstm_model.keras")
    model.save(model_path)
    
    metrics_path = os.path.join(ARTIFACTS_DIR, "lstm_metrics.txt")
    with open(metrics_path, "w") as f:
        f.write(f"Multivariate TensorFlow LSTM MAE: {mae:.2f} vehicles/hr\n")
        f.write(f"Multivariate TensorFlow LSTM MAPE: {mape:.2f}%\n")
        if rf_mae and rf_mape:
            f.write(f"RandomForest Baseline MAE: {rf_mae:.2f} vehicles/hr\n")
            f.write(f"RandomForest Baseline MAPE: {rf_mape:.2f}%\n")
            
    print(f"Multivariate LSTM Model and metrics saved to {ARTIFACTS_DIR}")
    return mae, mape

if __name__ == "__main__":
    train_lstm()
