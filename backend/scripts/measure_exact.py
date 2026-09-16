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

# 1. Startup load time
t0 = time.perf_counter()
model = joblib.load(rf_path)
load_time_ms = (time.perf_counter() - t0) * 1000.0

# Critical Fix: n_jobs=1 for single-sample inference (disables joblib multi-thread pool Overhead)
model.n_jobs = 1

# 2. Input sample
X_sample = pd.DataFrame([{
    "hour": 17, "day_of_week": 2, "is_weekend": 0,
    "volume_lag_1h": 4200.0, "volume_lag_24h": 4100.0, "rolling_avg_3h": 4150.0,
    "temp": 22.5, "rain_1h": 0
}])

# Warmup (discard cold-start)
for _ in range(10):
    model.predict(X_sample)

# 3. Clean inference measurement loop
latencies = []
for _ in range(200):
    t_start = time.perf_counter()
    model.predict(X_sample)
    t_end = time.perf_counter()
    latencies.append((t_end - t_start) * 1000.0)

mean_latency = sum(latencies) / len(latencies)
min_latency = min(latencies)

print("="*60, flush=True)
print(f"Model Load Time (Startup)               : {load_time_ms:.2f} ms", flush=True)
print(f"Single-Thread (n_jobs=1) Pure Inference : {mean_latency:.4f} ms (Min: {min_latency:.4f} ms)", flush=True)
print("="*60, flush=True)
