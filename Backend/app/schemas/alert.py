"""
app/schemas/alert.py

Pydantic v2 schemas for the Traffic Alerts endpoints.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.alert import AlertSeverity, AlertStatus, AlertType


class AlertCreate(BaseModel):
    segment_id: uuid.UUID
    title: str = Field(min_length=5, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    alert_type: AlertType
    severity: AlertSeverity

    model_config = {
        "json_schema_extra": {
            "example": {
                "segment_id": "660e8400-e29b-41d4-a716-446655440001",
                "title": "Heavy congestion approaching peak hour",
                "description": "Vehicle count 312, speed dropped to 38 kmh.",
                "alert_type": "CONGESTION",
                "severity": "HIGH"
            }
        }
    }


class AlertUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=5, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    severity: AlertSeverity | None = Field(default=None)


class AlertRead(BaseModel):
    id: uuid.UUID
    segment_id: uuid.UUID
    created_by: uuid.UUID | None
    
    title: str
    description: str | None
    
    alert_type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }
