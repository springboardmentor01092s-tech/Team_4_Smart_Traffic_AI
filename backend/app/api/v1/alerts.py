import json
import logging
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from app.services import notification_service
from app.core.mongodb import get_mongo_db

logger = logging.getLogger(__name__)

router = APIRouter()

ALERTS_FALLBACK_PATH = Path("data/alerts_fallback.json")

@router.get("/")
def list_alerts(resolved: bool = False):
    """Lists alerts filtered by their resolved status."""
    db = get_mongo_db()
    if db is not None:
        try:
            alerts = list(db.traffic_alerts.find({"resolved": resolved}))
            for a in alerts:
                a["_id"] = str(a["_id"])
            return alerts
        except Exception as e:
            logger.warning(f"Failed to query alerts from MongoDB: {e}. Falling back to local file.")
            
    # Fallback to local file
    alerts = []
    if ALERTS_FALLBACK_PATH.exists():
        try:
            with open(ALERTS_FALLBACK_PATH, "r") as f:
                alerts = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read local fallback alerts: {e}")
            alerts = []
            
    filtered = [a for a in alerts if a.get("resolved") == resolved]
    return filtered

@router.post("/resolve")
def resolve_alert(junction_id: str, timestamp: str):
    """Marks a matching alert as resolved in MongoDB or local fallback storage."""
    db = get_mongo_db()
    resolved_in_mongo = False
    
    if db is not None:
        try:
            result = db.traffic_alerts.update_one(
                {"junction_id": junction_id, "timestamp": timestamp},
                {"$set": {"resolved": True}}
            )
            if result.modified_count > 0 or result.matched_count > 0:
                resolved_in_mongo = True
        except Exception as e:
            logger.warning(f"Failed to resolve alert in MongoDB: {e}")
            
    # Update local file as well, or as fallback
    resolved_locally = False
    if ALERTS_FALLBACK_PATH.exists():
        try:
            with open(ALERTS_FALLBACK_PATH, "r") as f:
                alerts = json.load(f)
            
            updated = False
            for a in alerts:
                if a.get("junction_id") == junction_id and a.get("timestamp") == timestamp:
                    a["resolved"] = True
                    updated = True
                    
            if updated:
                with open(ALERTS_FALLBACK_PATH, "w") as f:
                    json.dump(alerts, f, indent=2)
                resolved_locally = True
        except Exception as e:
            logger.error(f"Failed to resolve alert locally: {e}")
            
    if resolved_in_mongo or resolved_locally:
        return {"success": True, "message": f"Alert at {junction_id} resolved successfully."}
        
    raise HTTPException(status_code=404, detail="Alert not found or could not be updated.")

@router.websocket("/ws")
async def alerts_ws(websocket: WebSocket):
    """WebSocket connection for real-time alert broadcasts."""
    await websocket.accept()
    notification_service._active_websockets.append(websocket)
    logger.info("New WebSocket client connected to alerts channel.")
    try:
        while True:
            # Keep alive block
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    finally:
        if websocket in notification_service._active_websockets:
            notification_service._active_websockets.remove(websocket)
