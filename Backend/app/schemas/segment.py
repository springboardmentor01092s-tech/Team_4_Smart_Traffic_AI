"""
app/schemas/segment.py

Pydantic v2 schemas for the Traffic Segments endpoints.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.segment import SegmentStatus


class SegmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    start_point: str = Field(min_length=2, max_length=255)
    end_point: str = Field(min_length=2, max_length=255)
    
    start_latitude: float = Field(ge=-90.0, le=90.0)
    start_longitude: float = Field(ge=-180.0, le=180.0)
    end_latitude: float = Field(ge=-90.0, le=90.0)
    end_longitude: float = Field(ge=-180.0, le=180.0)
    
    length_km: float = Field(gt=0.0)
    speed_limit_kmh: int = Field(ge=1, le=300)
    
    camera_id: uuid.UUID | None = Field(default=None)
    status: SegmentStatus = Field(default=SegmentStatus.ACTIVE)

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "NH-1 Sector 14 to Sector 18",
                "start_point": "Sector 14 Flyover",
                "end_point": "Sector 18 Interchange",
                "start_latitude": 28.6820,
                "start_longitude": 77.1025,
                "end_latitude": 28.6530,
                "end_longitude": 77.0840,
                "length_km": 4.2,
                "speed_limit_kmh": 80,
                "camera_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "status": "ACTIVE"
            }
        }
    }


class SegmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    start_point: str | None = Field(default=None, min_length=2, max_length=255)
    end_point: str | None = Field(default=None, min_length=2, max_length=255)
    
    start_latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    start_longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    end_latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    end_longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    
    length_km: float | None = Field(default=None, gt=0.0)
    speed_limit_kmh: int | None = Field(default=None, ge=1, le=300)
    
    camera_id: uuid.UUID | None = Field(default=None)
    status: SegmentStatus | None = Field(default=None)


class SegmentRead(BaseModel):
    id: uuid.UUID
    name: str
    start_point: str
    end_point: str
    
    start_latitude: float
    start_longitude: float
    end_latitude: float
    end_longitude: float
    
    length_km: float
    speed_limit_kmh: int
    
    camera_id: uuid.UUID | None
    status: SegmentStatus
    
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }
