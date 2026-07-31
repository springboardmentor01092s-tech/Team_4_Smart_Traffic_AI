import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.segment import CongestionLevel


class ReadingCreate(BaseModel):
    segment_id: uuid.UUID = Field(..., description="ID of the monitored traffic segment")
    vehicle_count: int = Field(..., ge=0, description="Number of vehicles recorded")
    average_speed_kmh: float = Field(..., ge=0.0, description="Average speed in km/h")
    congestion_level: CongestionLevel = Field(..., description="Calculated or observed congestion level")
    occupancy_percent: Optional[float] = Field(None, ge=0.0, le=100.0, description="Percentage of road area occupied")
    recorded_at: datetime = Field(..., description="UTC time when the measurement was taken")


class ReadingRead(ReadingCreate):
    id: int = Field(..., description="Unique integer ID for the reading")
    created_at: datetime = Field(..., description="UTC timestamp of insertion into the database")

    model_config = ConfigDict(from_attributes=True)
