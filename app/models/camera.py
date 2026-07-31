"""
app/models/camera.py

SQLAlchemy 2.x ORM model for the TrafficCamera entity.

Owned by Backend Developer #2.

A TrafficCamera represents a physical surveillance camera installed at a road
location. It is the infrastructure root of the traffic monitoring system;
TrafficSegment records optionally reference cameras.

Soft-deletion: setting deleted_at to a UTC timestamp hides the record from
all normal queries without physically removing it. The relationship with
traffic_segments uses SET NULL so segments survive camera soft-deletion.

Fields:
    id              UUID primary key (client-generated via uuid.uuid4)
    name            Human-readable camera label
    location_name   Textual description of the installation location
    latitude        Geographic latitude of the camera (-90 to 90)
    longitude       Geographic longitude of the camera (-180 to 180)
    status          CameraStatus enum value
    description     Optional free-text notes
    installed_at    When the camera was physically installed (UTC)
    created_at      Record creation timestamp (UTC)
    updated_at      Record last-updated timestamp (UTC)
    deleted_at      Soft-delete timestamp; NULL means the record is active (UTC)
"""
import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CameraStatus(str, Enum):
    """
    Operational state of a physical traffic camera.

    Inherits from str so Pydantic and JSON serialization work without
    extra conversion — the value IS the string representation.

    ACTIVE:      Camera is online and collecting data.
    INACTIVE:    Camera is installed but not currently operating.
    MAINTENANCE: Planned maintenance; data may be unreliable.
    OFFLINE:     Camera is unreachable or has failed unexpectedly.
    """

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"
    OFFLINE = "OFFLINE"


class TrafficCamera(Base):
    """ORM model representing a physical traffic surveillance camera."""

    __tablename__ = "traffic_cameras"

    # ─── Primary Key ─────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Universally unique identifier for the camera.",
    )

    # ─── Identity ────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Human-readable camera label (2–100 chars).",
    )
    location_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Textual description of the camera installation location (2–255 chars).",
    )

    # ─── Geographic Position ─────────────────────────────────────────────────
    latitude: Mapped[float] = mapped_column(
        nullable=False,
        doc="Geographic latitude of the camera. Must be between -90.0 and 90.0.",
    )
    longitude: Mapped[float] = mapped_column(
        nullable=False,
        doc="Geographic longitude of the camera. Must be between -180.0 and 180.0.",
    )

    # ─── Status ──────────────────────────────────────────────────────────────
    status: Mapped[CameraStatus] = mapped_column(
        String(20),
        nullable=False,
        default=CameraStatus.ACTIVE,
        doc="Operational status of the camera. Defaults to ACTIVE.",
    )

    # ─── Optional Details ────────────────────────────────────────────────────
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        doc="Optional free-text notes about the camera (max 500 chars).",
    )

    # ─── Timestamps ──────────────────────────────────────────────────────────
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        doc="UTC timestamp of when the camera was physically installed.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        doc="UTC timestamp of record creation.",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        doc="UTC timestamp of the most recent update.",
    )

    # ─── Soft Delete ─────────────────────────────────────────────────────────
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        doc=(
            "Soft-delete timestamp. NULL means the record is active. "
            "Set to UTC now() to logically delete without a physical DELETE."
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<TrafficCamera id={self.id} name={self.name!r} "
            f"status={self.status} deleted={self.deleted_at is not None}>"
        )
