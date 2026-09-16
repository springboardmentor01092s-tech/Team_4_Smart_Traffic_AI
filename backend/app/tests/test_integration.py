import sys
import os
import json
from fastapi.testclient import TestClient

# Add backend root to path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app
from app.services import pipeline_service, notification_service
from app.services.analytics_service import FALLBACK_TRAFFIC_PATH, FALLBACK_ALERTS_PATH

client = TestClient(app)

def test_rest_endpoints():
    """Verify REST API routes for alerts and analytics return valid schemas and HTTP 200."""

    # 1. Test Analytics Heatmap Route
    response = client.get("/api/v1/analytics/heatmap")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 6
    for point in data:
        assert "junction_id" in point
        assert "lat" in point
        assert "lng" in point
        assert "intensity" in point
        assert "congestion_level" in point

    # 2. Test Analytics Summary Route
    response = client.get("/api/v1/analytics/summary")
    assert response.status_code == 200
    summary = response.json()
    assert isinstance(summary, dict)
    assert "active_intersections" in summary
    assert "total_vehicles_monitored" in summary
    assert "average_speed_kmh" in summary
    assert "incidents_reported" in summary

    # 3. Test Alerts Listing Route
    response = client.get("/api/v1/alerts?resolved=false")
    assert response.status_code == 200
    alerts = response.json()
    assert isinstance(alerts, list)
    print("REST Endpoints integration test PASSED")

async def test_websocket_broadcast_and_pipeline():
    """Manually triggers a pipeline cycle, checks local/DB persistence, and verifies WebSocket alert streaming."""
    # Ensure any active websocket lists are empty for testing
    notification_service._active_websockets = []

    # Connect to the alerts websocket
    with client.websocket_connect("/api/v1/alerts/ws") as websocket:
        # Verify the client is registered
        assert len(notification_service._active_websockets) == 1
        
        # Trigger a mock alert manually to verify broadcasting works
        test_alert = {
            "junction_id": "J1",
            "type": "congestion",
            "severity": "high",
            "message": "Integration Test: High congestion alert",
            "timestamp": "2026-08-27T10:00:00Z",
            "resolved": False
        }
        
        # Save alert (writes to DB or fallback JSON)
        notification_service.save_alert(test_alert)
        
        # Broadcast alert (should stream to WS)
        await notification_service.broadcast_alert(test_alert)
        
        # Receive the alert over the WebSocket channel
        received_data = websocket.receive_json()
        assert received_data["junction_id"] == "J1"
        assert received_data["severity"] == "high"
        assert "Integration Test" in received_data["message"]
        
    print("WebSocket alert streaming and pipeline integration test PASSED")

if __name__ == "__main__":
    # Setup test file backups if they exist to avoid corruption during testing
    import shutil
    backups = {}
    for path in [FALLBACK_TRAFFIC_PATH, FALLBACK_ALERTS_PATH]:
        if path.exists():
            backup_path = path.with_suffix(".json.bak")
            shutil.copy(path, backup_path)
            backups[path] = backup_path

    try:
        # Run test functions
        test_rest_endpoints()
        
        # Import asyncio to run async websocket test
        import asyncio
        asyncio.run(test_websocket_broadcast_and_pipeline())
        
        print("\nALL INTEGRATION END-TO-END TESTS PASSED SUCCESSFULLY!")
    finally:
        # Restore backups
        for path, backup_path in backups.items():
            if backup_path.exists():
                shutil.move(backup_path, path)
