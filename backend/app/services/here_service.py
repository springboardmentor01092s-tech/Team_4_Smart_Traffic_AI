import urllib.request
import urllib.parse
import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class HEREService:
    """Helper client service to interact with HERE Traffic Flow API."""

    def __init__(self):
        self.api_key = settings.HERE_API_KEY
        self.base_url = "https://data.traffic.hereapi.com/v7/flow"

    def get_flow_data(self, bbox: str) -> dict:
        """
        Retrieves real-time traffic flow (speed, jam factor, free flow speed) inside a bounding box.
        Format of bbox: "minLon,minLat,maxLon,maxLat"
        API Docs: https://developer.here.com/documentation/traffic-api/dg/flow-request-examples.html
        """
        if not self.api_key:
            logger.warning("HERE_API_KEY is not configured. Returning high-fidelity mock flow data.")
            return self._get_mock_flow_data(bbox)

        # HERE uses bbox format in:bbox:minLon,minLat,maxLon,maxLat
        url = f"{self.base_url}?locationReferencing=shape&in=bbox:{bbox}&apiKey={self.api_key}"
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    return json.loads(response.read().decode())
                else:
                    raise Exception(f"HERE Traffic Flow API returned status: {response.status}")
        except Exception as e:
            logger.error(f"Error fetching traffic flow data from HERE: {e}. Falling back to mock data.")
            return self._get_mock_flow_data(bbox)

    def _get_mock_flow_data(self, bbox: str) -> dict:
        """Returns mock HERE flow data for local testing."""
        import random
        # Split bbox to estimate coordinate centers
        try:
            coords = [float(x) for x in bbox.split(",")]
            center_lon = (coords[0] + coords[2]) / 2.0
            center_lat = (coords[1] + coords[3]) / 2.0
        except Exception:
            center_lat, center_lon = 12.9715987, 77.5945627

        # Randomize flow parameters for simulation
        free_flow = 60.0
        speed = random.choice([18.5, 32.0, 45.5, 52.0])
        jam_factor = round(((free_flow - speed) / free_flow) * 10.0, 1)

        return {
          "results": [
            {
              "location": {
                "description": "MG Road Corridor Main Arterial Link",
                "shape": {
                  "links": [
                    {
                      "points": [
                        {"lat": center_lat, "lng": center_lon},
                        {"lat": center_lat + 0.001, "lng": center_lon + 0.001}
                      ]
                    }
                  ]
                }
              },
              "currentFlow": {
                "speed": speed,
                "speedUncapped": speed,
                "freeFlow": free_flow,
                "jamFactor": jam_factor,
                "confidence": 0.98
              }
            }
          ]
        }
