"""
app/schemas/incident.py

Pydantic v2 schemas for the Incident Ingestion endpoints.
"""
import uuid
from pydantic import BaseModel, Field

from app.models.alert import AlertSeverity, AlertType


class IncidentCreate(BaseModel):
    segment_id: uuid.UUID
    title: str = Field(min_length=5, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    incident_type: AlertType
    severity: AlertSeverity

    model_config = {
        "json_schema_extra": {
            "example": {
                "segment_id": "660e8400-e29b-41d4-a716-446655440001",
                "title": "Multi-vehicle collision on Northbound lane",
                "description": "2 cars involved, blocking right lane.",
                "incident_type": "ACCIDENT",
                "severity": "CRITICAL"
            }
        }
    }
