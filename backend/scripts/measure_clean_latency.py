import time
import os
import joblib
import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACTS_DIR = os.path.join(BASE_DIR, "app", "ml", "artifacts")
rf_path = os.path.join(ARTIFACTS_DIR, "traffic_model.pkl")

# 1. One-time load time
t0 = time.perf_counter()
model = joblib.load(rf_path)
model.n_jobs = 1
load_time_ms = (time.perf_counter() - t0) * 1000.0

# 2. Input sample
X_sample = pd.DataFrame([{
    "hour": 17, "day_of_week": 2, "is_weekend": 0,
    "volume_lag_1h": 4200.0, "volume_lag_24h": 4100.0, "rolling_avg_3h": 4150.0,
    "temp": 22.5, "rain_1h": 0
}])

# 3. Warm-up calls (discarded)
for _ in range(10):
    model.predict(X_sample)

# 4. Pure inference timing over 100 iterations
latencies = []
for _ in range(100):
    t_start = time.perf_counter()
    model.predict(X_sample)
    latencies.append((time.perf_counter() - t_start) * 1000.0)

mean_latency_ms = sum(latencies) / len(latencies)
min_latency_ms = min(latencies)

print("="*60, flush=True)
print(f"RandomForest Model Load Time (Startup): {load_time_ms:.2f} ms", flush=True)
print(f"RandomForest Pure Inference Mean      : {mean_latency_ms:.4f} ms", flush=True)
print(f"RandomForest Pure Inference Min       : {min_latency_ms:.4f} ms", flush=True)
print("="*60, flush=True)
