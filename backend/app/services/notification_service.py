"""
notification_service.py
Persists alerts to MongoDB (fallback: local JSON) and broadcasts over WebSocket.
"""
import json
import logging
from pathlib import Path
from app.core.mongodb import get_mongo_db

logger = logging.getLogger(__name__)

ALERTS_FALLBACK_PATH = Path("data/alerts_fallback.json")
_active_websockets = []  # populated by the WebSocket route

async def broadcast_alert(alert: dict):
    """Broadcasts a new alert to all active WebSocket clients."""
    # Ensure any ObjectId is stringified or popped for JSON serialization
    serialized_alert = alert.copy()
    if "_id" in serialized_alert:
        serialized_alert["_id"] = str(serialized_alert["_id"])
        
    for ws in list(_active_websockets):
        try:
            await ws.send_json(serialized_alert)
        except Exception as e:
            logger.debug(f"Removing inactive WebSocket: {e}")
            if ws in _active_websockets:
                _active_websockets.remove(ws)

def save_alert(alert: dict):
    """Saves alert to MongoDB or local fallback JSON file."""
    # Make a copy to avoid mutating the original dict in-place
    alert_to_save = alert.copy()
    
    db = get_mongo_db()
    if db is not None:
        try:
            db.traffic_alerts.insert_one(alert_to_save)
            return
        except Exception as e:
            logger.warning(f"MongoDB write failed: {e}. Storing locally.")
            alert_to_save.pop("_id", None)
            
    _append_local_fallback(alert_to_save)

def _append_local_fallback(alert: dict):
    """Appends alert to local JSON fallback store."""
    existing = []
    try:
        ALERTS_FALLBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
        if ALERTS_FALLBACK_PATH.exists():
            with open(ALERTS_FALLBACK_PATH, "r") as f:
                try:
                    existing = json.load(f)
                except Exception:
                    existing = []
                    
        existing.append(alert)
        with open(ALERTS_FALLBACK_PATH, "w") as f:
            json.dump(existing, f, indent=2)
            
        logger.info(f"Saved alert observation locally to {ALERTS_FALLBACK_PATH}")
    except Exception as e:
        logger.error(f"Failed to write fallback alert locally: {e}")
