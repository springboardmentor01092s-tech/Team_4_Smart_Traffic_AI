"""
app/models/segment.py

SQLAlchemy 2.x ORM model for the TrafficSegment entity.
"""
import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SegmentStatus(str, Enum):
    """
    Operational state of a traffic segment.
    """
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    UNDER_MAINTENANCE = "UNDER_MAINTENANCE"
    CLOSED = "CLOSED"


class CongestionLevel(str, Enum):
    """
    Congestion level of a traffic segment/reading.
    """
    FREE_FLOW = "FREE_FLOW"
    LIGHT = "LIGHT"
    MODERATE = "MODERATE"
    HEAVY = "HEAVY"
    STANDSTILL = "STANDSTILL"


class TrafficSegment(Base):
    """ORM model representing a monitored road segment."""

    __tablename__ = "traffic_segments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    start_point: Mapped[str] = mapped_column(String(255), nullable=False)
    end_point: Mapped[str] = mapped_column(String(255), nullable=False)

    start_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    start_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    end_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    end_longitude: Mapped[float] = mapped_column(Float, nullable=False)

    length_km: Mapped[float] = mapped_column(Float, nullable=False)
    speed_limit_kmh: Mapped[int] = mapped_column(Integer, nullable=False)

    camera_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("traffic_cameras.id", ondelete="SET NULL"),
        nullable=True,
    )

    status: Mapped[SegmentStatus] = mapped_column(
        SAEnum(SegmentStatus, name="segment_status", native_enum=True, create_type=False),
        nullable=False,
        default=SegmentStatus.ACTIVE,
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
            f"<TrafficSegment id={self.id} name={self.name!r} "
            f"status={self.status} deleted={self.deleted_at is not None}>"
        )
