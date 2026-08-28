import sys
import os

# Add backend root to path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services import alert_service, analytics_service

def test_congestion_alerts():
    # 1. Congestion level High, delay > 10 => High severity alert
    alert = alert_service.evaluate_congestion_alert("J1", "High", 3500.0, 15.2)
    assert alert is not None
    assert alert["junction_id"] == "J1"
    assert alert["type"] == alert_service.AlertType.CONGESTION
    assert alert["severity"] == alert_service.AlertSeverity.HIGH
    assert "High congestion" in alert["message"]

    # 2. Congestion level High, delay <= 10 => Moderate severity alert
    alert = alert_service.evaluate_congestion_alert("J2", "High", 2800.0, 8.5)
    assert alert is not None
    assert alert["severity"] == alert_service.AlertSeverity.MODERATE

    # 3. Congestion level Moderate => No alert
    alert = alert_service.evaluate_congestion_alert("J3", "Moderate", 2400.0, 4.0)
    assert alert is None
    print("test_congestion_alerts PASSED")

def test_accident_alerts():
    incidents = [
        {"type": "Accident", "description": "Accident blocking right lane"},
        {"type": "Road Work", "description": "Lane painting"},
        {"type": "Crash", "description": "Minor crash at intersection"}
    ]
    
    alerts = alert_service.evaluate_accident_alerts("J1", incidents)
    assert len(alerts) == 2
    assert alerts[0]["junction_id"] == "J1"
    assert alerts[0]["type"] == alert_service.AlertType.ACCIDENT
    assert alerts[0]["severity"] == alert_service.AlertSeverity.HIGH
    assert "Accident" in alerts[0]["message"] or "crash" in alerts[0]["message"].lower()
    print("test_accident_alerts PASSED")

def test_analytics_summary():
    summary = analytics_service.get_summary()
    assert isinstance(summary, dict)
    assert "active_intersections" in summary
    assert "total_vehicles_monitored" in summary
    assert "average_speed_kmh" in summary
    assert "system_status" in summary
    assert "incidents_reported" in summary
    assert summary["active_intersections"] == 6
    print("test_analytics_summary PASSED")

def test_analytics_heatmap():
    heatmap_data = analytics_service.get_heatmap_data()
    assert isinstance(heatmap_data, list)
    assert len(heatmap_data) == 6
    for point in heatmap_data:
        assert "junction_id" in point
        assert "lat" in point
        assert "lng" in point
        assert "intensity" in point
        assert "congestion_level" in point
    print("test_analytics_heatmap PASSED")

if __name__ == "__main__":
    test_congestion_alerts()
    test_accident_alerts()
    test_analytics_summary()
    test_analytics_heatmap()
    print("\nALL ALERTS & ANALYTICS TESTS PASSED SUCCESSFULLY!")
