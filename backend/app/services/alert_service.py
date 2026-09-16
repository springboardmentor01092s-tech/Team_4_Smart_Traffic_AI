"""
alert_service.py
Evaluates real-time observations + model predictions and produces alerts.
"""
from datetime import datetime, timezone
from enum import Enum

class AlertType(str, Enum):
    CONGESTION = "congestion"
    ACCIDENT = "accident"

class AlertSeverity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"

def evaluate_congestion_alert(junction_id: str, congestion_level: str, volume: float, delay_min: float):
    """Returns an alert dict if congestion_level == 'High', else None."""
    if congestion_level != "High":
        return None
        
    return {
        "junction_id": junction_id,
        "type": AlertType.CONGESTION,
        "severity": AlertSeverity.HIGH if delay_min > 10 else AlertSeverity.MODERATE,
        "message": f"High congestion at {junction_id}: {volume:.0f} veh/hr, ~{delay_min:.1f} min delay",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resolved": False,
    }

def evaluate_accident_alerts(junction_id: str, incidents: list):
    """
    Filters incoming incidents for accident/crash reports and returns formatted alert dicts.
    incidents: list of incident dicts returned by TomTomService.get_incidents()
    """
    alerts = []
    for incident in incidents:
        # Check both the 'type' field and the 'description' field for crash/accident indicators
        incident_type = incident.get("type", "").lower()
        description = incident.get("description", "").lower()
        
        is_accident = any(kw in incident_type or kw in description for kw in ["accident", "crash", "collision"])
        
        if is_accident:
            alerts.append({
                "junction_id": junction_id,
                "type": AlertType.ACCIDENT,
                "severity": AlertSeverity.HIGH,
                "message": incident.get("description", f"Accident reported near {junction_id}"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "resolved": False,
            })
    return alerts
