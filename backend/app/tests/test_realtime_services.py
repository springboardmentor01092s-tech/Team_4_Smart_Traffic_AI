import sys
import os

# Add backend root to path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.tomtom_service import TomTomService
from app.services.here_service import HEREService

def test_tomtom_service_fallback():
    service = TomTomService()
    # If API key is empty, it should use high-fidelity mock data safely
    service.api_key = ""
    
    # Test flow segment data retrieval
    flow_data = service.get_flow_data(lat=12.9716, lon=77.5946)
    assert "flowSegmentData" in flow_data
    assert "currentSpeed" in flow_data["flowSegmentData"]
    assert "freeFlowSpeed" in flow_data["flowSegmentData"]
    
    # Test incident data retrieval
    incidents = service.get_incidents("77.5900,12.9700,77.6000,12.9800")
    assert isinstance(incidents, list)
    assert len(incidents) > 0
    assert "location" in incidents[0]
    assert "severity" in incidents[0]
    print("test_tomtom_service_fallback PASSED")

def test_here_service_fallback():
    service = HEREService()
    service.api_key = ""
    
    # Test flow data retrieval
    flow_data = service.get_flow_data("77.5900,12.9700,77.6000,12.9800")
    assert "results" in flow_data
    assert len(flow_data["results"]) > 0
    assert "currentFlow" in flow_data["results"][0]
    assert "speed" in flow_data["results"][0]["currentFlow"]
    assert "jamFactor" in flow_data["results"][0]["currentFlow"]
    print("test_here_service_fallback PASSED")

if __name__ == "__main__":
    test_tomtom_service_fallback()
    test_here_service_fallback()
    print("\nALL REAL-TIME SERVICE TESTS PASSED SUCCESSFULLY!")
