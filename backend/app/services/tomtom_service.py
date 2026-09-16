import urllib.request
import urllib.parse
import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class TomTomService:
    """Helper client service to interact with TomTom Traffic Flow and Incidents API."""

    def __init__(self):
        self.api_key = settings.TOMTOM_API_KEY
        self.base_url = "https://api.tomtom.com/traffic/services/4"

    def get_flow_data(self, lat: float, lon: float, zoom: int = 12) -> dict:
        """
        Retrieves real-time traffic flow speed and travel time for a specific point.
        API Docs: https://developer.tomtom.com/traffic-flow-api/documentation/traffic-flow/flow-segment-data
        """
        if not self.api_key:
            logger.warning("TOMTOM_API_KEY is not configured. Returning high-fidelity mock flow data.")
            return self._get_mock_flow_data(lat, lon)

        url = f"{self.base_url}/flowSegmentData/relative-compact/{zoom}/json?key={self.api_key}&point={lat},{lon}&unit=KMPH"
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    return json.loads(response.read().decode())
                else:
                    raise Exception(f"TomTom Flow API returned status: {response.status}")
        except Exception as e:
            logger.error(f"Error fetching traffic flow data from TomTom: {e}. Falling back to mock data.")
            return self._get_mock_flow_data(lat, lon)

    def get_incidents(self, bbox: str, zoom: int = 12) -> list:
        """
        Retrieves real-time traffic incidents (accidents, construction, delays) inside a bounding box.
        Format of bbox: "minLon,minLat,maxLon,maxLat"
        API Docs: https://developer.tomtom.com/traffic-incidents-api/documentation/traffic-incidents/incident-details
        """
        if not self.api_key:
            logger.warning("TOMTOM_API_KEY is not configured. Returning high-fidelity mock incidents.")
            return self._get_mock_incidents()

        # TomTom Incident Details uses a bounding box in format minLon,minLat,maxLon,maxLat
        url = f"{self.base_url}/incidentDetails/s3/{bbox}/{zoom}/-1/json?key={self.api_key}&originalPosition=true"
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    return self._parse_incidents(data)
                else:
                    raise Exception(f"TomTom Incidents API returned status: {response.status}")
        except Exception as e:
            logger.error(f"Error fetching traffic incidents from TomTom: {e}. Falling back to mock incidents.")
            return self._get_mock_incidents()

    def _parse_incidents(self, raw_data: dict) -> list:
        """Parses TomTom incident response format into standardized layout."""
        incidents = []
        try:
            # TomTom incident response uses tm -> poi array
            tm = raw_data.get("tm", {})
            poi_list = tm.get("poi", [])
            for i, poi in enumerate(poi_list):
                severity_map = {0: "Unknown", 1: "Low", 2: "Medium", 3: "High", 4: "Critical"}
                incidents.append({
                    "id": f"tomtom-{i}-{poi.get('id', '')}",
                    "location": poi.get("f", "Unknown Location"),
                    "type": poi.get("d", "Traffic Hazard"),
                    "severity": severity_map.get(poi.get("ic", 1), "Medium"),
                    "description": poi.get("c", "Traffic delay reported by TomTom"),
                    "reported_at": "Just now",
                    "status": "Active"
                })
        except Exception as e:
            logger.error(f"Failed to parse TomTom raw incidents: {e}")
        return incidents

    def _get_mock_flow_data(self, lat: float, lon: float) -> dict:
        """Returns mock segment flow data for local testing."""
        import random
        # Randomize current speed slightly to simulate real traffic changes
        free_flow_speed = 60
        current_speed = random.choice([22, 35, 48, 55])
        current_travel_time = int(120 * (free_flow_speed / current_speed))
        free_flow_travel_time = 120
        
        return {
            "flowSegmentData": {
                "frc": "FRC3",
                "currentSpeed": current_speed,
                "freeFlowSpeed": free_flow_speed,
                "currentTravelTime": current_travel_time,
                "freeFlowTravelTime": free_flow_travel_time,
                "confidence": 0.95,
                "coordinates": {
                    "coordinate": [
                        {"latitude": lat, "longitude": lon}
                    ]
                }
            }
        }

    def _get_mock_incidents(self) -> list:
        """Returns mock incidents for local testing."""
        return [
            {
                "id": "tomtom-mock-1",
                "location": "MG Road Corridor - Junction 4",
                "type": "Accident",
                "severity": "High",
                "description": "TomTom Realtime: Two-vehicle collision blocking right lane.",
                "reported_at": "10 mins ago",
                "status": "Active"
            },
            {
                "id": "tomtom-mock-2",
                "location": "Outer Ring Road Exit 12",
                "type": "Road Work",
                "severity": "Medium",
                "description": "TomTom Realtime: Lane reduction for asphalt resurfacing.",
                "reported_at": "25 mins ago",
                "status": "Active"
            }
        ]
