from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.prediction import PredictionStatus
from app.models.segment import CongestionLevel


class PredictionCreate(BaseModel):
    """Schema for requesting a new traffic prediction."""
    segment_id: UUID
    prediction_for: datetime
    horizon_minutes: int = Field(..., gt=0)
    model_version: str | None = None


class PredictionComplete(BaseModel):
    """Schema for submitting the result of a prediction."""
    predicted_congestion_level: CongestionLevel
    predicted_vehicle_count: int | None = Field(default=None, ge=0)
    predicted_avg_speed_kmh: float | None = Field(default=None, ge=0.0)
    confidence_score: float = Field(..., ge=0.0, le=1.0)


class PredictionRead(BaseModel):
    """Schema for returning a traffic prediction."""
    id: UUID
    segment_id: UUID
    predicted_congestion_level: CongestionLevel | None
    predicted_vehicle_count: int | None
    predicted_avg_speed_kmh: float | None
    confidence_score: float | None
    prediction_for: datetime
    horizon_minutes: int
    status: PredictionStatus
    model_version: str | None
    requested_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
