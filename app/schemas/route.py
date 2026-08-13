"""
app/schemas/route.py

Pydantic v2 schemas for the Routes module.

Milestone 2 additions:
  TravelTimeEstimateRead  — response for GET /routes/{id}/estimate
  RouteComparisonItem     — per-route entry in comparison response
  RouteComparisonRead     — response for GET /routes/compare
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.segment import CongestionLevel


# ── Request Schemas ───────────────────────────────────────────────────────────

class RouteCreate(BaseModel):
    """Validated input for creating a new route."""

    name: str = Field(..., min_length=2, max_length=150)
    origin_name: str = Field(..., min_length=2, max_length=255)
    destination_name: str = Field(..., min_length=2, max_length=255)
    total_distance_km: float = Field(..., gt=0.0, description="Total route distance in kilometres")


class RouteUpdate(BaseModel):
    """
    Partial update input for an existing route.
    Only explicitly provided fields are applied; all fields are optional.
    """

    name: str | None = Field(default=None, min_length=2, max_length=150)
    origin_name: str | None = Field(default=None, min_length=2, max_length=255)
    destination_name: str | None = Field(default=None, min_length=2, max_length=255)
    total_distance_km: float | None = Field(default=None, gt=0.0)
    is_active: bool | None = None


class RouteSegmentAdd(BaseModel):
    """Validated input for adding a segment to a route."""

    segment_id: UUID
    sequence_order: int = Field(..., ge=1, description="Position of this segment within the route (1-indexed)")


# ── Response Schemas ──────────────────────────────────────────────────────────

class RouteSegmentRead(BaseModel):
    """Response representation of a single route_segments join row."""

    id: UUID
    route_id: UUID
    segment_id: UUID
    sequence_order: int

    model_config = ConfigDict(from_attributes=True)


class RouteRead(BaseModel):
    """Standard response schema for route list, create, and update operations."""

    id: UUID
    name: str
    origin_name: str
    destination_name: str
    total_distance_km: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RouteDetailRead(RouteRead):
    """
    Extended response for GET /routes/{id}.

    Includes the ordered list of segment join rows so callers know which
    segments belong to this route and in what order.
    deleted_at is excluded, consistent with all other module response schemas.
    """

    route_segments: list[RouteSegmentRead] = []


class SegmentTrafficItem(BaseModel):
    """
    Per-segment traffic snapshot inside a RouteTrafficRead response.

    Fields are nullable because not all segments may have readings.
    Segment names are excluded to avoid N+1 DB lookups on every /traffic call.
    """

    segment_id: UUID
    congestion_level: CongestionLevel | None
    vehicle_count: int | None
    average_speed_kmh: float | None
    recorded_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class RouteTrafficRead(BaseModel):
    """
    Aggregated current traffic state across all segments of a route.

    worst_congestion_level is None when no segment in the route has any reading.
    Congestion severity ordering: STANDSTILL > HEAVY > MODERATE > LIGHT > FREE_FLOW.
    """

    route_id: UUID
    route_name: str
    worst_congestion_level: CongestionLevel | None
    segment_count: int
    segments_with_readings: int
    segment_traffic: list[SegmentTrafficItem]


# ── Milestone 2: Travel Time Estimate ────────────────────────────────────────

class SegmentEstimateItem(BaseModel):
    """Per-segment breakdown inside a TravelTimeEstimateRead."""

    segment_id: UUID
    segment_name: str
    length_km: float
    speed_used_kmh: float
    estimated_minutes: float
    data_source: str  # "reading" or "speed_limit"


class TravelTimeEstimateRead(BaseModel):
    """Response for GET /routes/{route_id}/estimate."""

    route_id: UUID
    route_name: str
    total_distance_km: float
    estimated_travel_minutes: float
    worst_congestion_level: CongestionLevel | None
    segments_with_readings: int
    segment_count: int
    segment_estimates: list[SegmentEstimateItem]


# ── Milestone 2: Route Comparison ────────────────────────────────────────────

class RouteComparisonItem(BaseModel):
    """Per-route entry in a route comparison response."""

    route_id: UUID
    route_name: str
    origin_name: str
    destination_name: str
    total_distance_km: float
    estimated_travel_minutes: float
    worst_congestion_level: CongestionLevel | None
    segments_with_readings: int
    segment_count: int
    rank: int
    is_recommended: bool
    recommendation_reason: str


class RouteComparisonRead(BaseModel):
    """Response for GET /routes/compare."""

    recommended_route_id: UUID | None
    routes: list[RouteComparisonItem]
