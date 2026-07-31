"""
app/models/prediction.py

SQLAlchemy 2.x ORM model for the TrafficPrediction entity.
"""
import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.segment import CongestionLevel


class PredictionStatus(str, Enum):
    """Lifecycle status of a traffic prediction."""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TrafficPrediction(Base):
    """ORM model representing a forecast of traffic conditions."""

    __tablename__ = "traffic_predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    segment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("traffic_segments.id", ondelete="RESTRICT"),
        nullable=False,
    )

    predicted_congestion_level: Mapped[CongestionLevel | None] = mapped_column(
        SAEnum(CongestionLevel, name="congestion_level", create_type=False, native_enum=True),
        nullable=True,
        default=None,
    )

    predicted_vehicle_count: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    predicted_avg_speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)

    prediction_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    horizon_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[PredictionStatus] = mapped_column(
        SAEnum(PredictionStatus, name="prediction_status", create_type=False, native_enum=True),
        nullable=False,
        default=PredictionStatus.PENDING,
    )
    
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    def __repr__(self) -> str:
        return (
            f"<TrafficPrediction id={self.id} segment_id={self.segment_id} "
            f"status={self.status} prediction_for={self.prediction_for} "
            f"deleted={self.deleted_at is not None}>"
        )
