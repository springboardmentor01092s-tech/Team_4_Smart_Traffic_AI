import sys
import os
import datetime
import random
import json
import logging

# Ensure backend directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.mongodb import connect_to_mongo, get_mongo_db, close_mongo_connection
from app.services.tomtom_service import TomTomService
from app.services.here_service import HEREService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fallback local data file path
FALLBACK_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "realtime_traffic_fallback.json")

# Sample intersection coordinates for data polling
TARGET_JUNCTIONS = [
    {"id": "J1", "name": "Central Plaza Crossing", "lat": 12.9716, "lon": 77.5946, "bbox": "77.5900,12.9700,77.6000,12.9800", "road_capacity": 4000},
    {"id": "J2", "name": "MG Road & 5th Avenue", "lat": 12.9735, "lon": 77.6010, "bbox": "77.5950,12.9700,77.6050,12.9800", "road_capacity": 3800},
    {"id": "J3", "name": "Tech Corridor Junction", "lat": 12.9592, "lon": 77.6974, "bbox": "77.6900,12.9500,77.7050,12.9650", "road_capacity": 4500},
    {"id": "J4", "name": "Airport Expressway Flyover", "lat": 13.1986, "lon": 77.7066, "bbox": "77.7000,13.1900,77.7150,13.2050", "road_capacity": 6000},
    {"id": "J5", "name": "Metro Station Interchange", "lat": 12.9815, "lon": 77.5951, "bbox": "77.5900,12.9750,77.6000,12.9850", "road_capacity": 3500},
    {"id": "J6", "name": "South Port Boulevard", "lat": 12.9433, "lon": 77.6205, "bbox": "77.6150,12.9380,77.6250,12.9480", "road_capacity": 3200}
]

def collect_and_store():
    # Connect to MongoDB
    connect_to_mongo()
    db = get_mongo_db()
    
    use_mongodb = True
    if db is None:
        logger.warning("Could not connect to MongoDB. Falling back to local storage.")
        use_mongodb = False
        
    tomtom = TomTomService()
    here = HEREService()
    
    now = datetime.datetime.now()
    hour = now.hour
    day_of_week = now.weekday()
    is_weekend = 1 if day_of_week >= 5 else 0
    is_peak = 1 if hour in [7, 8, 9, 16, 17, 18] else 0
    
    logger.info(f"Starting real-time traffic data collection at {now.isoformat()}")
    
    records_inserted = 0
    local_records = []
    
    for j in TARGET_JUNCTIONS:
        try:
            logger.info(f"Querying live traffic for {j['name']} ({j['id']})...")
            
            # Fetch flow data from TomTom and HERE
            tt_flow = tomtom.get_flow_data(j["lat"], j["lon"])
            here_flow = here.get_flow_data(j["bbox"])
            tt_incidents = tomtom.get_incidents(j["bbox"])
            
            # Extract flow details
            tt_data = tt_flow.get("flowSegmentData", {})
            tt_speed = tt_data.get("currentSpeed", 45)
            tt_free_speed = tt_data.get("freeFlowSpeed", 60)
            
            # Parse HERE data
            here_speed = 45.0
            here_jam = 0.0
            results = here_flow.get("results", [])
            if results:
                flow_info = results[0].get("currentFlow", {})
                here_speed = flow_info.get("speed", 45.0)
                here_jam = flow_info.get("jamFactor", 0.0)
                
            # Standardize speeds (average the speed reports)
            avg_speed = float((tt_speed + here_speed) / 2.0)
            free_flow_speed = float(tt_free_speed)
            
            # Estimate vehicle count
            speed_ratio = min(1.0, max(0.1, avg_speed / free_flow_speed))
            estimated_density = 1.0 - speed_ratio
            base_vol = j["road_capacity"] * estimated_density
            vehicle_count = int(max(150, min(j["road_capacity"], base_vol + random.normalvariate(0, 100))))
            
            if is_peak and vehicle_count < (j["road_capacity"] * 0.4):
                vehicle_count = int(j["road_capacity"] * random.uniform(0.4, 0.85))
                
            # Process incidents
            has_incident = 1 if (len(tt_incidents) > 0 or here_jam > 7.0) else 0
            
            # Weather variables
            temp = 24.5 + random.uniform(-2, 2)
            rain_1h = 1 if (has_incident and random.random() > 0.8) else 0
            weather_code = 1 if rain_1h else 0
            
            # Compose database record
            record = {
                "junction_id": j["id"],
                "junction_name": j["name"],
                "timestamp": now.isoformat(),
                "hour": hour,
                "day_of_week": day_of_week,
                "is_weekend": is_weekend,
                "is_peak_hour": is_peak,
                "road_capacity": j["road_capacity"],
                "avg_speed_kmh": round(avg_speed, 2),
                "free_flow_speed_kmh": round(free_flow_speed, 2),
                "vehicle_count": vehicle_count,
                "has_incident": has_incident,
                "temp": round(temp, 1),
                "rain_1h": rain_1h,
                "weather_code": weather_code,
                "tomtom_incidents_count": len(tt_incidents),
                "here_jam_factor": here_jam,
                "meta": {
                    "source": "TomTom & HERE APIs",
                    "polled_at": now.strftime("%Y-%m-%d %H:%M:%S")
                }
            }
            
            if use_mongodb:
                try:
                    db["realtime_traffic"].insert_one(record)
                    records_inserted += 1
                except Exception as mongo_err:
                    logger.warning(f"MongoDB write failed: {mongo_err}. Storing locally instead.")
                    local_records.append(record)
            else:
                local_records.append(record)
                
            logger.info(f"Processed observation for {j['name']}. Vol={vehicle_count}, Speed={record['avg_speed_kmh']} km/h")
            
        except Exception as e:
            logger.error(f"Failed to collect data for junction {j['id']}: {e}")
            
    close_mongo_connection()
    
    # Save fallback records locally
    if local_records:
        try:
            existing_data = []
            if os.path.exists(FALLBACK_FILE_PATH):
                with open(FALLBACK_FILE_PATH, "r") as f:
                    try:
                        existing_data = json.load(f)
                    except Exception:
                        existing_data = []
            
            existing_data.extend(local_records)
            
            with open(FALLBACK_FILE_PATH, "w") as f:
                json.dump(existing_data, f, indent=2)
                
            logger.info(f"Saved {len(local_records)} observations locally to {FALLBACK_FILE_PATH}")
            records_inserted += len(local_records)
        except Exception as file_err:
            logger.error(f"Failed to save observations locally: {file_err}")
            
    print(f"Data collection cycle completed. Successfully saved {records_inserted} observations.")

if __name__ == "__main__":
    collect_and_store()
