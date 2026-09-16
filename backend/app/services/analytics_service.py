"""
analytics_service.py
Aggregates historical observations for dashboards and heatmaps.
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from app.core.mongodb import get_mongo_db

logger = logging.getLogger(__name__)

FALLBACK_TRAFFIC_PATH = Path("data/realtime_traffic_fallback.json")
FALLBACK_ALERTS_PATH = Path("data/alerts_fallback.json")

JUNCTION_COORDS = {
    "J1": {"name": "Central Plaza Crossing", "lat": 12.9716, "lng": 77.5946},
    "J2": {"name": "MG Road & 5th Avenue", "lat": 12.9735, "lng": 77.6010},
    "J3": {"name": "Tech Corridor Junction", "lat": 12.9592, "lng": 77.6974},
    "J4": {"name": "Airport Expressway Flyover", "lat": 13.1986, "lng": 77.7066},
    "J5": {"name": "Metro Station Interchange", "lat": 12.9815, "lng": 77.5951},
    "J6": {"name": "South Port Boulevard", "lat": 12.9433, "lng": 77.6205}
}

def get_heatmap_data():
    """Returns the latest congestion snapshot per junction, for map heatmap layer."""
    db = get_mongo_db()
    latest_observations = {}
    
    if db is not None:
        try:
            latest = db.realtime_traffic.aggregate([
                {"$sort": {"timestamp": -1}},
                {"$group": {"_id": "$junction_id", "doc": {"$first": "$$ROOT"}}},
            ])
            for entry in latest:
                latest_observations[entry["_id"]] = entry["doc"]
        except Exception as e:
            logger.warning(f"Failed to aggregate heatmap from MongoDB: {e}. Checking local cache.")
            
    # Fallback to local cache if MongoDB aggregation yielded no data
    if not latest_observations and FALLBACK_TRAFFIC_PATH.exists():
        try:
            with open(FALLBACK_TRAFFIC_PATH, "r") as f:
                records = json.load(f)
            # Sort chronologically, then group by junction_id keeping the latest
            records_sorted = sorted(records, key=lambda x: x.get("timestamp", ""))
            for r in records_sorted:
                jid = r.get("junction_id")
                if jid:
                    latest_observations[jid] = r
        except Exception as e:
            logger.error(f"Failed to read local traffic cache for heatmap: {e}")
            
    points = []
    for jid, coords in JUNCTION_COORDS.items():
        obs = latest_observations.get(jid, {})
        points.append({
            "junction_id": jid,
            "name": coords["name"],
            "lat": coords["lat"],
            "lng": coords["lng"],
            "intensity": obs.get("vehicle_count", 0),
            "congestion_level": obs.get("congestion_level", "Low"),
            "avg_speed_kmh": obs.get("avg_speed_kmh", 50.0),
            "timestamp": obs.get("timestamp", "")
        })
    return points

def get_trends(junction_id: str, hours: int = 24):
    """Returns time series of volume/delay for a junction, for line charts."""
    db = get_mongo_db()
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    if db is not None:
        try:
            cursor = db.realtime_traffic.find(
                {"junction_id": junction_id, "timestamp": {"$gte": since}}
            ).sort("timestamp", 1)
            results = list(cursor)
            for r in results:
                r["_id"] = str(r["_id"])
                # Convert datetime object to ISO format for uniform API returns
                if isinstance(r.get("timestamp"), datetime):
                    r["timestamp"] = r["timestamp"].isoformat()
            return results
        except Exception as e:
            logger.warning(f"Failed to query trends from MongoDB: {e}. Falling back to local cache.")
            
    # Local fallback logic
    results = []
    if FALLBACK_TRAFFIC_PATH.exists():
        try:
            with open(FALLBACK_TRAFFIC_PATH, "r") as f:
                records = json.load(f)
                
            for r in records:
                if r.get("junction_id") != junction_id:
                    continue
                    
                t_str = r.get("timestamp", "")
                try:
                    # Remove 'Z' if present, replace with offset to parse cleanly
                    if t_str.endswith('Z'):
                        t_str = t_str[:-1] + '+00:00'
                    t_val = datetime.fromisoformat(t_str)
                    
                    if t_val.tzinfo is None:
                        t_val = t_val.replace(tzinfo=timezone.utc)
                    else:
                        t_val = t_val.astimezone(timezone.utc)
                        
                    if t_val >= since:
                        results.append(r)
                except Exception as parse_err:
                    logger.debug(f"Failed to parse fallback timestamp '{t_str}': {parse_err}")
                    # Include it anyway if parsing fails but ID matches as a fail-safe
                    results.append(r)
                    
            results = sorted(results, key=lambda x: x.get("timestamp", ""))
        except Exception as e:
            logger.error(f"Failed to read local trends cache: {e}")
            
    return results

def get_summary():
    """Computes dashboard summary statistics."""
    heatmap = get_heatmap_data()
    
    total_vehicles = sum(p["intensity"] for p in heatmap)
    speeds = [p["avg_speed_kmh"] for p in heatmap if p["intensity"] > 0]
    avg_speed = round(sum(speeds) / len(speeds), 1) if speeds else 50.0
    
    # Check if any junction is highly congested
    has_high_congestion = any(p["congestion_level"] == "High" for p in heatmap)
    system_status = "Heavy Congestion" if has_high_congestion else "Optimal"
    
    # Query count of unresolved active alerts
    db = get_mongo_db()
    active_alerts_count = 0
    
    if db is not None:
        try:
            active_alerts_count = db.traffic_alerts.count_documents({"resolved": False})
        except Exception as e:
            logger.warning(f"Failed to count active alerts in MongoDB: {e}")
            
    if db is None or active_alerts_count == 0:
        if FALLBACK_ALERTS_PATH.exists():
            try:
                with open(FALLBACK_ALERTS_PATH, "r") as f:
                    alerts = json.load(f)
                active_alerts_count = sum(1 for a in alerts if not a.get("resolved"))
            except Exception as e:
                logger.error(f"Failed to parse fallback alerts for summary: {e}")
                
    return {
        "active_intersections": len(JUNCTION_COORDS),
        "total_vehicles_monitored": total_vehicles,
        "average_speed_kmh": avg_speed,
        "system_status": system_status,
        "incidents_reported": active_alerts_count
    }
