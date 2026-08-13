import sys
import os

# Add backend root to path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.ml.congestion import (
    load_models,
    prepare_congestion_features,
    forecast_congestion,
    forecast_delay,
    generate_forecast
)


def test_prepare_congestion_features():
    df = prepare_congestion_features(
        hour=8,
        day_of_week=1,
        volume_lag_1h=2500,
        volume_lag_24h=2400,
        rolling_avg_3h=2450,
        temp=25.0,
        rain_1h=0.0
    )
    assert len(df) == 1
    assert df.iloc[0]["is_weekend"] == 0
    assert df.iloc[0]["hour"] == 8
    print("test_prepare_congestion_features PASSED")


def test_forecast_congestion():
    level = forecast_congestion(
        hour=8,
        day_of_week=1,
        volume_lag_1h=2500,
        volume_lag_24h=2400,
        rolling_avg_3h=2450,
        temp=25.0,
        rain_1h=0.0
    )
    assert isinstance(level, str)
    assert level in ["Low", "Moderate", "High"]
    print(f"test_forecast_congestion PASSED (level: {level})")


def test_forecast_delay():
    delay = forecast_delay(
        vehicle_count=2500,
        avg_speed_kmh=35.0,
        road_capacity=3000,
        is_peak_hour=True,
        weather_code=0,
        has_incident=False
    )
    assert isinstance(delay, float)
    assert delay >= 0.0
    print(f"test_forecast_delay PASSED (delay: {delay} mins)")


def test_generate_forecast():
    result = generate_forecast(
        hour=8,
        day_of_week=1,
        volume_lag_1h=2500,
        volume_lag_24h=2400,
        rolling_avg_3h=2450,
        temp=25.0,
        rain_1h=0.0,
        vehicle_count=2500,
        avg_speed_kmh=35.0,
        road_capacity=3000,
        is_peak_hour=True,
        weather_code=0,
        has_incident=False
    )

    assert "forecast" in result
    assert "traffic_conditions" in result
    assert "forecast_context" in result
    assert result["forecast"]["congestion_level"] == "Moderate"
    assert result["forecast"]["predicted_delay_minutes"] == 34.62
    assert result["traffic_conditions"]["vehicle_count"] == 2500
    assert result["forecast_context"]["hour"] == 8
    print("test_generate_forecast PASSED")


if __name__ == "__main__":
    test_prepare_congestion_features()
    test_forecast_congestion()
    test_forecast_delay()
    test_generate_forecast()
    print("\nALL CONGESTION MODULE TESTS PASSED SUCCESSFULLY!")
