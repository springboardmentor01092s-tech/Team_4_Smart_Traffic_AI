"""
app/models/alert.py

SQLAlchemy 2.x ORM model for the TrafficAlert entity.
"""
import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AlertType(str, Enum):
    """Classifies the nature of the traffic incident."""
    CONGESTION = "CONGESTION"
    ACCIDENT = "ACCIDENT"
    ROAD_CLOSURE = "ROAD_CLOSURE"
    WEATHER = "WEATHER"
    EMERGENCY = "EMERGENCY"
    ROADWORKS = "ROADWORKS"


class AlertSeverity(str, Enum):
    """Indicates urgency and impact of the alert."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, Enum):
    """Tracks the operational lifecycle of an alert."""
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class Alert(Base):
    """ORM model representing a traffic incident alert."""

    __tablename__ = "alerts"

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

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    alert_type: Mapped[AlertType] = mapped_column(SAEnum(AlertType, name="alert_type", create_type=False, native_enum=True), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(SAEnum(AlertSeverity, name="alert_severity", create_type=False, native_enum=True), nullable=False)
    status: Mapped[AlertStatus] = mapped_column(
        SAEnum(AlertStatus, name="alert_status", create_type=False, native_enum=True),
        nullable=False,
        default=AlertStatus.ACTIVE,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
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
            f"<Alert id={self.id} title={self.title!r} "
            f"status={self.status} deleted={self.deleted_at is not None}>"
        )
