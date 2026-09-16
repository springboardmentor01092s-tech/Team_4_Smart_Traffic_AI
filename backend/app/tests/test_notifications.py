import sys
import os
from fastapi.testclient import TestClient

# Add backend root to path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app

client = TestClient(app)

def test_get_notifications():
    response = client.get("/api/v1/traffic/notifications")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    assert "text" in data[0]
    print("test_get_notifications PASSED")

def test_clear_notifications():
    # Clear
    response = client.post("/api/v1/traffic/notifications/clear")
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Check they are cleared
    response = client.get("/api/v1/traffic/notifications")
    assert response.status_code == 200
    assert len(response.json()) == 0
    print("test_clear_notifications PASSED")

def test_incident_notification_trigger():
    # Report incident
    payload = {
        "location": "MG Road Test Location",
        "type": "Accident",
        "severity": "High",
        "description": "Test collision"
    }
    response = client.post("/api/v1/traffic/incidents", json=payload)
    assert response.status_code == 200

    # Check notification was added
    response = client.get("/api/v1/traffic/notifications")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert "MG Road Test Location" in data[0]["text"]
    assert data[0]["type"] == "danger"
    print("test_incident_notification_trigger PASSED")

if __name__ == "__main__":
    test_get_notifications()
    test_clear_notifications()
    test_incident_notification_trigger()
    print("\nALL NOTIFICATION TESTS PASSED SUCCESSFULLY!")
