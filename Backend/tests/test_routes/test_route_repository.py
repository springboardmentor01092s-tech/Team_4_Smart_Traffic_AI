"""
tests/test_routes/test_route_repository.py

Unit tests for RouteRepository and RouteSegment operations.

Uses the in-memory SQLite test_db fixture from conftest.py.
All tests are function-scoped for complete isolation.

Coverage:
  - Route create / get_by_id / get_by_id_with_segments / get_all / soft_delete
  - RouteSegment add_segment / get_route_segment / remove_segment
  - get_segment_ids_for_route (ordering verified)
  - check_sequence_order_taken
  - Soft-delete visibility (get_by_id returns None after soft_delete)
  - Pagination (skip / limit)
  - is_active filter
"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.route import Route, RouteSegment
from app.models.segment import TrafficSegment
from app.repositories.route_repository import RouteRepository


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _make_segment(db: AsyncSession) -> TrafficSegment:
    """Create a minimal TrafficSegment for FK references."""
    seg = TrafficSegment(
        name=f"Seg-{uuid.uuid4().hex[:6]}",
        start_point="A",
        end_point="B",
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


async def _make_route(
    db: AsyncSession,
    *,
    name: str = "Test Route",
    is_active: bool = True,
) -> Route:
    """Create a minimal Route."""
    route = Route(
        name=name,
        origin_name="Origin",
        destination_name="Destination",
        total_distance_km=10.0,
        is_active=is_active,
    )
    db.add(route)
    await db.flush()
    await db.refresh(route)
    return route


# ── Route read tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_route_defaults(test_db: AsyncSession) -> None:
    """Created route has expected defaults: is_active=True, deleted_at=None."""
    repo = RouteRepository(test_db)
    route = await repo.create(
        name="Highway 1",
        origin_name="City A",
        destination_name="City B",
        total_distance_km=55.5,
    )
    assert route.id is not None
    assert route.name == "Highway 1"
    assert route.is_active is True
    assert route.deleted_at is None
    assert route.total_distance_km == 55.5


@pytest.mark.asyncio
async def test_get_by_id_returns_route(test_db: AsyncSession) -> None:
    """get_by_id returns a route that exists and is not deleted."""
    route = await _make_route(test_db)
    repo = RouteRepository(test_db)
    fetched = await repo.get_by_id(route.id)
    assert fetched is not None
    assert fetched.id == route.id


@pytest.mark.asyncio
async def test_get_by_id_nonexistent(test_db: AsyncSession) -> None:
    """get_by_id returns None for a random UUID."""
    repo = RouteRepository(test_db)
    result = await repo.get_by_id(uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_soft_deleted_returns_none(test_db: AsyncSession) -> None:
    """get_by_id returns None when the route is soft-deleted."""
    route = await _make_route(test_db)
    repo = RouteRepository(test_db)
    await repo.soft_delete(route)
    result = await repo.get_by_id(route.id)
    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_with_segments_loads_relationship(test_db: AsyncSession) -> None:
    """get_by_id_with_segments returns route with route_segments populated."""
    seg = await _make_segment(test_db)
    route = await _make_route(test_db)
    repo = RouteRepository(test_db)
    await repo.add_segment(route_id=route.id, segment_id=seg.id, sequence_order=1)

    fetched = await repo.get_by_id_with_segments(route.id)
    assert fetched is not None
    assert len(fetched.route_segments) == 1
    assert fetched.route_segments[0].segment_id == seg.id


@pytest.mark.asyncio
async def test_get_by_id_with_segments_soft_deleted_returns_none(test_db: AsyncSession) -> None:
    """get_by_id_with_segments respects soft-delete."""
    route = await _make_route(test_db)
    repo = RouteRepository(test_db)
    await repo.soft_delete(route)
    result = await repo.get_by_id_with_segments(route.id)
    assert result is None


@pytest.mark.asyncio
async def test_get_all_excludes_soft_deleted(test_db: AsyncSession) -> None:
    """get_all does not return soft-deleted routes."""
    repo = RouteRepository(test_db)
    r1 = await repo.create(name="R1", origin_name="O", destination_name="D", total_distance_km=1.0)
    r2 = await repo.create(name="R2", origin_name="O", destination_name="D", total_distance_km=2.0)
    await repo.soft_delete(r2)

    results = await repo.get_all()
    ids = [r.id for r in results]
    assert r1.id in ids
    assert r2.id not in ids


@pytest.mark.asyncio
async def test_get_all_filter_is_active(test_db: AsyncSession) -> None:
    """get_all(is_active=True/False) returns only matching routes."""
    repo = RouteRepository(test_db)
    active = await repo.create(name="Active", origin_name="O", destination_name="D", total_distance_km=1.0)
    inactive = await repo.create(name="Inactive", origin_name="O", destination_name="D", total_distance_km=1.0)
    await repo.update(inactive, is_active=False)

    active_results = await repo.get_all(is_active=True)
    inactive_results = await repo.get_all(is_active=False)

    active_ids = [r.id for r in active_results]
    inactive_ids = [r.id for r in inactive_results]

    assert active.id in active_ids
    assert inactive.id not in active_ids
    assert inactive.id in inactive_ids
    assert active.id not in inactive_ids


@pytest.mark.asyncio
async def test_get_all_pagination(test_db: AsyncSession) -> None:
    """Pagination skip/limit work correctly."""
    repo = RouteRepository(test_db)
    for i in range(5):
        await repo.create(name=f"R{i}", origin_name="O", destination_name="D", total_distance_km=float(i + 1))

    first_two = await repo.get_all(skip=0, limit=2)
    next_two = await repo.get_all(skip=2, limit=2)
    assert len(first_two) == 2
    assert len(next_two) == 2
    assert {r.id for r in first_two}.isdisjoint({r.id for r in next_two})


# ── Route write tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_route_fields(test_db: AsyncSession) -> None:
    """update() applies provided fields and refreshes the model."""
    route = await _make_route(test_db)
    repo = RouteRepository(test_db)
    updated = await repo.update(route, name="Updated Name", total_distance_km=99.9)
    assert updated.name == "Updated Name"
    assert updated.total_distance_km == 99.9


@pytest.mark.asyncio
async def test_soft_delete_sets_deleted_at(test_db: AsyncSession) -> None:
    """soft_delete sets deleted_at to a non-None datetime."""
    route = await _make_route(test_db)
    repo = RouteRepository(test_db)
    await repo.soft_delete(route)
    assert route.deleted_at is not None
    assert route.updated_at is not None


# ── RouteSegment tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_segment_creates_join_row(test_db: AsyncSession) -> None:
    """add_segment returns a RouteSegment with correct fields."""
    seg = await _make_segment(test_db)
    route = await _make_route(test_db)
    repo = RouteRepository(test_db)

    join_row = await repo.add_segment(route_id=route.id, segment_id=seg.id, sequence_order=1)
    assert join_row.id is not None
    assert join_row.route_id == route.id
    assert join_row.segment_id == seg.id
    assert join_row.sequence_order == 1


@pytest.mark.asyncio
async def test_get_route_segment_returns_join_row(test_db: AsyncSession) -> None:
    """get_route_segment returns the join row when it exists."""
    seg = await _make_segment(test_db)
    route = await _make_route(test_db)
    repo = RouteRepository(test_db)
    await repo.add_segment(route_id=route.id, segment_id=seg.id, sequence_order=1)

    result = await repo.get_route_segment(route.id, seg.id)
    assert result is not None
    assert result.segment_id == seg.id


@pytest.mark.asyncio
async def test_get_route_segment_not_found(test_db: AsyncSession) -> None:
    """get_route_segment returns None when segment is not in route."""
    route = await _make_route(test_db)
    repo = RouteRepository(test_db)
    result = await repo.get_route_segment(route.id, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_remove_segment_hard_deletes_join_row(test_db: AsyncSession) -> None:
    """remove_segment removes the join row; get_route_segment returns None after."""
    seg = await _make_segment(test_db)
    route = await _make_route(test_db)
    repo = RouteRepository(test_db)
    await repo.add_segment(route_id=route.id, segment_id=seg.id, sequence_order=1)

    await repo.remove_segment(route.id, seg.id)
    result = await repo.get_route_segment(route.id, seg.id)
    assert result is None


@pytest.mark.asyncio
async def test_get_segment_ids_for_route_ordered(test_db: AsyncSession) -> None:
    """get_segment_ids_for_route returns UUIDs ordered by sequence_order ASC."""
    seg1 = await _make_segment(test_db)
    seg2 = await _make_segment(test_db)
    seg3 = await _make_segment(test_db)
    route = await _make_route(test_db)
    repo = RouteRepository(test_db)

    # Add in non-sequential order to verify sorting.
    await repo.add_segment(route_id=route.id, segment_id=seg3.id, sequence_order=3)
    await repo.add_segment(route_id=route.id, segment_id=seg1.id, sequence_order=1)
    await repo.add_segment(route_id=route.id, segment_id=seg2.id, sequence_order=2)

    ids = await repo.get_segment_ids_for_route(route.id)
    assert list(ids) == [seg1.id, seg2.id, seg3.id]


@pytest.mark.asyncio
async def test_check_sequence_order_taken_true(test_db: AsyncSession) -> None:
    """check_sequence_order_taken returns True when order is already used."""
    seg = await _make_segment(test_db)
    route = await _make_route(test_db)
    repo = RouteRepository(test_db)
    await repo.add_segment(route_id=route.id, segment_id=seg.id, sequence_order=1)

    assert await repo.check_sequence_order_taken(route.id, 1) is True


@pytest.mark.asyncio
async def test_check_sequence_order_taken_false(test_db: AsyncSession) -> None:
    """check_sequence_order_taken returns False when order is free."""
    route = await _make_route(test_db)
    repo = RouteRepository(test_db)
    assert await repo.check_sequence_order_taken(route.id, 1) is False


@pytest.mark.asyncio
async def test_get_segment_ids_empty_route(test_db: AsyncSession) -> None:
    """get_segment_ids_for_route returns an empty sequence for a route with no segments."""
    route = await _make_route(test_db)
    repo = RouteRepository(test_db)
    ids = await repo.get_segment_ids_for_route(route.id)
    assert list(ids) == []
