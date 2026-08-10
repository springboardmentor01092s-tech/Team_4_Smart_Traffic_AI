import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Integer,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.segment import CongestionLevel


class TrafficReading(Base):
    __tablename__ = "traffic_readings"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    segment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("traffic_segments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    vehicle_count: Mapped[int] = mapped_column(nullable=False)
    average_speed_kmh: Mapped[float] = mapped_column(Float, nullable=False)
    congestion_level: Mapped[CongestionLevel] = mapped_column(
        Enum(CongestionLevel, name="congestion_level", native_enum=True, create_type=False),
        nullable=False,
    )
    occupancy_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("vehicle_count >= 0", name="ck_readings_vehicle_count"),
        CheckConstraint("average_speed_kmh >= 0", name="ck_readings_speed"),
        CheckConstraint("occupancy_percent >= 0 AND occupancy_percent <= 100", name="ck_readings_occupancy"),
        Index("ix_traffic_readings_segment_id", "segment_id"),
        Index("ix_traffic_readings_recorded_at", "recorded_at"),
        Index("ix_traffic_readings_segment_recorded", "segment_id", "recorded_at"),
    )
