"""
app/models/route.py

SQLAlchemy 2.x ORM models for the Route and RouteSegment entities.

Design decisions:
  - Route and RouteSegment are co-located in one file because their
    relationship is tightly coupled and co-locating avoids circular imports
    between two separate model files.
  - Route uses UUID primary key and soft-delete via deleted_at, consistent
    with all other soft-deleted entities in this project.
  - RouteSegment is a pure join entity: UUID PK, no deleted_at. Removal
    is always a hard delete of the join row.
  - The relationship uses selectinload-compatible lazy="select" so the
    router can choose between get_by_id (no segments) and
    get_by_id_with_segments (eager segments) without model changes.
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Route(Base):
    """
    ORM model representing a named, ordered path through traffic segments.

    A route is a container entity; it gains meaning through its ordered
    RouteSegment association records. is_active provides a business-level
    visibility toggle (hides without deleting). deleted_at provides the
    full soft-delete audit trail.
    """

    __tablename__ = "routes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    origin_name: Mapped[str] = mapped_column(String(255), nullable=False)
    destination_name: Mapped[str] = mapped_column(String(255), nullable=False)
    total_distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

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

    # Relationship to join table — ordered by sequence_order ASC.
    # cascade="all, delete-orphan" ensures ORM-level housekeeping matches
    # the DB-level ON DELETE CASCADE on route_id FK.
    route_segments: Mapped[list["RouteSegment"]] = relationship(
        "RouteSegment",
        back_populates="route",
        order_by="RouteSegment.sequence_order",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<Route id={self.id} name={self.name!r} "
            f"is_active={self.is_active} deleted={self.deleted_at is not None}>"
        )


class RouteSegment(Base):
    """
    ORM model for the route_segments join table.

    Expresses: 'Route R passes through Segment S in position N.'
    This is a pure join entity — no business lifecycle, no soft-delete.
    Removing a segment from a route is an explicit hard delete of this row.

    The unique constraint on (route_id, sequence_order) is enforced at both
    the service layer (check_sequence_order_taken) and the database level
    (UniqueConstraint in __table_args__) to prevent race conditions.
    """

    __tablename__ = "route_segments"
    __table_args__ = (
        UniqueConstraint("route_id", "sequence_order", name="uq_route_segment_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("routes.id", ondelete="CASCADE"),
        nullable=False,
    )
    segment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("traffic_segments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)

    route: Mapped["Route"] = relationship("Route", back_populates="route_segments")

    def __repr__(self) -> str:
        return (
            f"<RouteSegment id={self.id} route_id={self.route_id} "
            f"segment_id={self.segment_id} order={self.sequence_order}>"
        )
