"""
tests/test_routes/test_route_service.py

Unit tests for RouteService business logic.

Uses real repositories against the in-memory SQLite test_db fixture.
This provides realistic integration coverage without PostgreSQL.

Coverage:
  - Happy-path CRUD operations
  - Not-found exceptions for all entity lookups
  - RouteSequenceConflictError for duplicate sequence_order
  - SegmentNotFoundError when segment UUID is invalid
  - SegmentNotInRouteError when removing a non-member segment
  - get_route_traffic: worst congestion computation, empty segments, mixed readings
  - update_route: exclude_unset semantics (no-op on empty payload)
  - delete_route: soft-delete cascades correctly
"""
import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    RouteNotFoundError,
    RouteSequenceConflictError,
    SegmentNotFoundError,
    SegmentNotInRouteError,
)
from app.models.reading import TrafficReading
from app.models.segment import CongestionLevel, TrafficSegment
from app.repositories.reading_repository import ReadingRepository
from app.repositories.route_repository import RouteRepository
from app.repositories.segment_repository import SegmentRepository
from app.schemas.route import RouteCreate, RouteSegmentAdd, RouteUpdate
from app.services.route_service import RouteService


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_service(db: AsyncSession) -> RouteService:
    return RouteService(
        RouteRepository(db),
        SegmentRepository(db),
        ReadingRepository(db),
    )


# Valid RouteCreate payload that passes all Pydantic constraints (min_length=2).
ROUTE_DATA = RouteCreate(
    name="Main Route",
    origin_name="North City",
    destination_name="South City",
    total_distance_km=25.0,
)


async def make_route(db: AsyncSession, *, name: str = "Main Route") -> object:
    """Create a route via the service, bypassing schema each time."""
    svc = make_service(db)
    return await svc.create_route(RouteCreate(
        name=name,
        origin_name="North City",
        destination_name="South City",
        total_distance_km=10.0,
    ))


async def make_segment(db: AsyncSession) -> TrafficSegment:
    seg = TrafficSegment(
        name=f"Seg-{uuid.uuid4().hex[:6]}",
        start_point="Point A",
        end_point="Point B",
        start_latitude=1.0,
        start_longitude=1.0,
        end_latitude=2.0,
        end_longitude=2.0,
        length_km=1.0,
        speed_limit_kmh=60,
    )
    db.add(seg)
    await db.flush()
    await db.refresh(seg)
    return seg


async def make_reading(
    db: AsyncSession,
    segment_id: uuid.UUID,
    congestion_level: CongestionLevel = CongestionLevel.LIGHT,
) -> TrafficReading:
    reading = TrafficReading(
        segment_id=segment_id,
        vehicle_count=10,
        average_speed_kmh=60.0,
        congestion_level=congestion_level,
        recorded_at=datetime.now(UTC),
    )
    db.add(reading)
    await db.flush()
    await db.refresh(reading)
    return reading


# ── list_routes tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_routes_returns_all_non_deleted(test_db: AsyncSession) -> None:
    svc = make_service(test_db)
    route = await svc.create_route(ROUTE_DATA)
    routes = await svc.list_routes()
    assert any(r.id == route.id for r in routes)


@pytest.mark.asyncio
async def test_list_routes_excludes_soft_deleted(test_db: AsyncSession) -> None:
    svc = make_service(test_db)
    route = await svc.create_route(ROUTE_DATA)
    await svc.delete_route(route.id)
    routes = await svc.list_routes()
    assert all(r.id != route.id for r in routes)


# ── get_route tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_route_happy_path(test_db: AsyncSession) -> None:
    svc = make_service(test_db)
    route = await svc.create_route(ROUTE_DATA)
    fetched = await svc.get_route(route.id)
    assert fetched.id == route.id
    assert fetched.route_segments == []


@pytest.mark.asyncio
async def test_get_route_not_found(test_db: AsyncSession) -> None:
    svc = make_service(test_db)
    with pytest.raises(RouteNotFoundError):
        await svc.get_route(uuid.uuid4())


@pytest.mark.asyncio
async def test_get_route_soft_deleted_raises_not_found(test_db: AsyncSession) -> None:
    svc = make_service(test_db)
    route = await svc.create_route(ROUTE_DATA)
    await svc.delete_route(route.id)
    with pytest.raises(RouteNotFoundError):
        await svc.get_route(route.id)


# ── create_route tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_route_returns_route(test_db: AsyncSession) -> None:
    svc = make_service(test_db)
    data = RouteCreate(
        name="Highway 99",
        origin_name="North Station",
        destination_name="South Station",
        total_distance_km=120.5,
    )
    route = await svc.create_route(data)
    assert route.name == "Highway 99"
    assert route.is_active is True
    assert route.deleted_at is None


# ── update_route tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_route_changes_fields(test_db: AsyncSession) -> None:
    svc = make_service(test_db)
    route = await svc.create_route(ROUTE_DATA)
    updated = await svc.update_route(route.id, RouteUpdate(name="New Name"))
    assert updated.name == "New Name"


@pytest.mark.asyncio
async def test_update_route_noop_on_empty_payload(test_db: AsyncSession) -> None:
    """An empty RouteUpdate (no fields set) returns the route unchanged."""
    svc = make_service(test_db)
    route = await svc.create_route(ROUTE_DATA)
    updated = await svc.update_route(route.id, RouteUpdate())
    assert updated.name == route.name


@pytest.mark.asyncio
async def test_update_route_not_found(test_db: AsyncSession) -> None:
    svc = make_service(test_db)
    with pytest.raises(RouteNotFoundError):
        await svc.update_route(uuid.uuid4(), RouteUpdate(name="New Name"))


@pytest.mark.asyncio
async def test_update_route_is_active_toggle(test_db: AsyncSession) -> None:
    svc = make_service(test_db)
    route = await svc.create_route(ROUTE_DATA)
    updated = await svc.update_route(route.id, RouteUpdate(is_active=False))
    assert updated.is_active is False


# ── add_segment_to_route tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_segment_happy_path(test_db: AsyncSession) -> None:
    svc = make_service(test_db)
    seg = await make_segment(test_db)
    route = await svc.create_route(ROUTE_DATA)
    join_row = await svc.add_segment_to_route(route.id, RouteSegmentAdd(segment_id=seg.id, sequence_order=1))
    assert join_row.route_id == route.id
    assert join_row.segment_id == seg.id
    assert join_row.sequence_order == 1


@pytest.mark.asyncio
async def test_add_segment_route_not_found(test_db: AsyncSession) -> None:
    svc = make_service(test_db)
    seg = await make_segment(test_db)
    with pytest.raises(RouteNotFoundError):
        await svc.add_segment_to_route(uuid.uuid4(), RouteSegmentAdd(segment_id=seg.id, sequence_order=1))


@pytest.mark.asyncio
async def test_add_segment_segment_not_found(test_db: AsyncSession) -> None:
    svc = make_service(test_db)
    route = await svc.create_route(ROUTE_DATA)
    with pytest.raises(SegmentNotFoundError):
        await svc.add_segment_to_route(route.id, RouteSegmentAdd(segment_id=uuid.uuid4(), sequence_order=1))


@pytest.mark.asyncio
async def test_add_segment_sequence_conflict(test_db: AsyncSession) -> None:
    """Adding two segments at the same sequence_order raises RouteSequenceConflictError."""
    svc = make_service(test_db)
    seg1 = await make_segment(test_db)
    seg2 = await make_segment(test_db)
    route = await svc.create_route(ROUTE_DATA)
    await svc.add_segment_to_route(route.id, RouteSegmentAdd(segment_id=seg1.id, sequence_order=1))
    with pytest.raises(RouteSequenceConflictError):
        await svc.add_segment_to_route(route.id, RouteSegmentAdd(segment_id=seg2.id, sequence_order=1))


# ── remove_segment_from_route tests ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_remove_segment_happy_path(test_db: AsyncSession) -> None:
    svc = make_service(test_db)
    seg = await make_segment(test_db)
    route = await svc.create_route(ROUTE_DATA)
    await svc.add_segment_to_route(route.id, RouteSegmentAdd(segment_id=seg.id, sequence_order=1))
    await svc.remove_segment_from_route(route.id, seg.id)

    route_detail = await svc.get_route(route.id)
    assert len(route_detail.route_segments) == 0


@pytest.mark.asyncio
async def test_remove_segment_route_not_found(test_db: AsyncSession) -> None:
    svc = make_service(test_db)
    seg = await make_segment(test_db)
    with pytest.raises(RouteNotFoundError):
        await svc.remove_segment_from_route(uuid.uuid4(), seg.id)


@pytest.mark.asyncio
async def test_remove_segment_not_in_route(test_db: AsyncSession) -> None:
    svc = make_service(test_db)
    seg = await make_segment(test_db)
    route = await svc.create_route(ROUTE_DATA)
    with pytest.raises(SegmentNotInRouteError):
        await svc.remove_segment_from_route(route.id, seg.id)


# ── delete_route tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_route_sets_deleted_at(test_db: AsyncSession) -> None:
    svc = make_service(test_db)
    route = await svc.create_route(ROUTE_DATA)
    await svc.delete_route(route.id)
    with pytest.raises(RouteNotFoundError):
        await svc.get_route(route.id)


@pytest.mark.asyncio
async def test_delete_route_not_found(test_db: AsyncSession) -> None:
    svc = make_service(test_db)
    with pytest.raises(RouteNotFoundError):
        await svc.delete_route(uuid.uuid4())


# ── get_route_traffic tests ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_route_traffic_not_found(test_db: AsyncSession) -> None:
    svc = make_service(test_db)
    with pytest.raises(RouteNotFoundError):
        await svc.get_route_traffic(uuid.uuid4())


@pytest.mark.asyncio
async def test_get_route_traffic_no_segments(test_db: AsyncSession) -> None:
    """Route with no segments returns empty traffic, worst_congestion_level=None."""
    svc = make_service(test_db)
    route = await svc.create_route(ROUTE_DATA)
    traffic = await svc.get_route_traffic(route.id)
    assert traffic.route_id == route.id
    assert traffic.worst_congestion_level is None
    assert traffic.segment_count == 0
    assert traffic.segments_with_readings == 0
    assert traffic.segment_traffic == []


@pytest.mark.asyncio
async def test_get_route_traffic_no_readings(test_db: AsyncSession) -> None:
    """Route with segments but no readings has worst_congestion_level=None."""
    svc = make_service(test_db)
    seg = await make_segment(test_db)
    route = await svc.create_route(ROUTE_DATA)
    await svc.add_segment_to_route(route.id, RouteSegmentAdd(segment_id=seg.id, sequence_order=1))

    traffic = await svc.get_route_traffic(route.id)
    assert traffic.segment_count == 1
    assert traffic.segments_with_readings == 0
    assert traffic.worst_congestion_level is None
    assert traffic.segment_traffic[0].congestion_level is None


@pytest.mark.asyncio
async def test_get_route_traffic_worst_congestion_computed(test_db: AsyncSession) -> None:
    """Worst congestion level is STANDSTILL when one segment has STANDSTILL reading."""
    svc = make_service(test_db)
    seg1 = await make_segment(test_db)
    seg2 = await make_segment(test_db)
    route = await svc.create_route(ROUTE_DATA)
    await svc.add_segment_to_route(route.id, RouteSegmentAdd(segment_id=seg1.id, sequence_order=1))
    await svc.add_segment_to_route(route.id, RouteSegmentAdd(segment_id=seg2.id, sequence_order=2))

    await make_reading(test_db, seg1.id, CongestionLevel.LIGHT)
    await make_reading(test_db, seg2.id, CongestionLevel.STANDSTILL)

    traffic = await svc.get_route_traffic(route.id)
    assert traffic.worst_congestion_level == CongestionLevel.STANDSTILL
    assert traffic.segments_with_readings == 2


@pytest.mark.asyncio
async def test_get_route_traffic_single_reading(test_db: AsyncSession) -> None:
    """Single segment with MODERATE reading returns MODERATE as worst."""
    svc = make_service(test_db)
    seg = await make_segment(test_db)
    route = await svc.create_route(ROUTE_DATA)
    await svc.add_segment_to_route(route.id, RouteSegmentAdd(segment_id=seg.id, sequence_order=1))
    await make_reading(test_db, seg.id, CongestionLevel.MODERATE)

    traffic = await svc.get_route_traffic(route.id)
    assert traffic.worst_congestion_level == CongestionLevel.MODERATE
    assert traffic.segment_traffic[0].vehicle_count == 10
