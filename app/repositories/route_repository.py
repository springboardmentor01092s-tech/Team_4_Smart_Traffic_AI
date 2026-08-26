"""
app/repositories/route_repository.py

Data access layer for the Route and RouteSegment entities.

Repository responsibilities:
  - All CRUD operations on routes and route_segments tables.
  - Soft-delete convention: get_by_id and get_all always filter deleted_at IS NULL.
  - No business logic. No exception raising for domain rules.
  - No HTTP concepts.

Soft-delete behaviour:
  - soft_delete() sets deleted_at = now() and updated_at = now(); calls flush().
  - No hard-delete method is exposed for Route (admin purge is offline).
  - remove_segment() issues a hard DELETE on the route_segments join row.

Session naming: self._db — consistent with CameraRepository, SegmentRepository,
AlertRepository, and PredictionRepository.
"""
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.route import Route, RouteSegment

logger = get_logger(__name__)


class RouteRepository:
    """
    Repository for Route and RouteSegment database operations.

    All read methods implicitly filter deleted_at IS NULL on the routes table.
    The route_segments table has no deleted_at; reads are unrestricted.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Route reads ───────────────────────────────────────────────────────────

    async def get_by_id(self, route_id: uuid.UUID) -> Route | None:
        """
        Fetch a non-deleted route by UUID (no segments loaded).

        Use get_by_id_with_segments when the route_segments list is needed.
        """
        result = await self._db.execute(
            select(Route).where(
                Route.id == route_id,
                Route.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_ids(
        self, route_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, Route]:
        """
        Batch-fetches active (non-deleted) routes by UUID.
        Returns a mapping of {route_id: Route}.
        """
        if not route_ids:
            return {}
        result = await self._db.execute(
            select(Route).where(
                Route.id.in_(route_ids),
                Route.deleted_at.is_(None),
            )
        )
        routes = result.scalars().all()
        return {r.id: r for r in routes}

    async def get_by_id_with_segments(self, route_id: uuid.UUID) -> Route | None:
        """
        Fetch a non-deleted route by UUID with its route_segments eagerly loaded.

        Uses selectinload to emit a second SELECT for route_segments, which is
        compatible with async SQLAlchemy. The relationship already orders by
        sequence_order via the ORM mapping.
        """
        result = await self._db.execute(
            select(Route)
            .options(selectinload(Route.route_segments))
            .where(
                Route.id == route_id,
                Route.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Route]:
        """
        Paginated list of non-deleted routes, optionally filtered by is_active.

        Args:
            is_active: If provided, filters routes with matching is_active value.
                       If None, returns both active and inactive routes.
            skip:      Pagination offset.
            limit:     Maximum rows returned.
        """
        stmt = select(Route).where(Route.deleted_at.is_(None))
        if is_active is not None:
            stmt = stmt.where(Route.is_active == is_active)
        stmt = stmt.order_by(Route.created_at.desc()).offset(skip).limit(limit)
        result = await self._db.execute(stmt)
        return result.scalars().all()

    # ── Route writes ──────────────────────────────────────────────────────────

    async def create(
        self,
        *,
        name: str,
        origin_name: str,
        destination_name: str,
        total_distance_km: float,
    ) -> Route:
        """
        Insert a new Route and return it with all defaults applied.

        is_active defaults to True (model default).
        deleted_at defaults to None (model default).
        """
        route = Route(
            name=name,
            origin_name=origin_name,
            destination_name=destination_name,
            total_distance_km=total_distance_km,
        )
        self._db.add(route)
        await self._db.flush()
        await self._db.refresh(route)
        logger.info("Route created | id=%s | name=%r", route.id, route.name)
        return route

    async def update(self, route: Route, **fields: object) -> Route:
        """
        Apply a set of field updates to an existing Route instance.

        Only fields present in `fields` are written; unchanged fields are
        preserved. Always call flush + refresh to get DB-computed values.
        """
        for field, value in fields.items():
            setattr(route, field, value)
        self._db.add(route)
        await self._db.flush()
        await self._db.refresh(route)
        logger.info("Route updated | id=%s | fields=%s", route.id, list(fields.keys()))
        return route

    async def soft_delete(self, route: Route) -> None:
        """
        Soft-delete a route by setting deleted_at and updated_at to now().

        Does NOT hard-delete the row. Subsequent get_by_id / get_all calls
        will exclude this route because deleted_at IS NOT NULL.
        """
        now = datetime.now(UTC)
        route.deleted_at = now
        route.updated_at = now
        self._db.add(route)
        await self._db.flush()
        logger.warning("Route soft-deleted | id=%s | name=%r", route.id, route.name)

    # ── RouteSegment reads ────────────────────────────────────────────────────

    async def get_route_segment(
        self,
        route_id: uuid.UUID,
        segment_id: uuid.UUID,
    ) -> RouteSegment | None:
        """
        Fetch a specific join row by (route_id, segment_id).

        Used by the service to verify segment membership before removal.
        Returns None if the segment is not part of the route.
        """
        result = await self._db.execute(
            select(RouteSegment).where(
                RouteSegment.route_id == route_id,
                RouteSegment.segment_id == segment_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_segment_ids_for_route(
        self, route_id: uuid.UUID
    ) -> Sequence[uuid.UUID]:
        """
        Return an ordered list of segment UUIDs for a route.

        Results are ordered by sequence_order ASC, matching the logical
        travel direction of the route.
        """
        result = await self._db.execute(
            select(RouteSegment.segment_id)
            .where(RouteSegment.route_id == route_id)
            .order_by(RouteSegment.sequence_order.asc())
        )
        return result.scalars().all()

    async def check_sequence_order_taken(
        self,
        route_id: uuid.UUID,
        sequence_order: int,
    ) -> bool:
        """
        Return True if the given sequence_order is already used in this route.

        Called by the service before attempting add_segment so the error is
        a clean domain exception rather than a DB IntegrityError.
        """
        result = await self._db.execute(
            select(RouteSegment.id).where(
                RouteSegment.route_id == route_id,
                RouteSegment.sequence_order == sequence_order,
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_routes_by_segment_id(self, segment_id: uuid.UUID) -> Sequence[Route]:
        """
        Return non-deleted routes that contain the given segment.
        """
        stmt = (
            select(Route)
            .join(RouteSegment, Route.id == RouteSegment.route_id)
            .where(
                RouteSegment.segment_id == segment_id,
                Route.deleted_at.is_(None)
            )
        )
        result = await self._db.execute(stmt)
        return result.scalars().all()

    # ── RouteSegment writes ───────────────────────────────────────────────────

    async def add_segment(
        self,
        *,
        route_id: uuid.UUID,
        segment_id: uuid.UUID,
        sequence_order: int,
    ) -> RouteSegment:
        """
        Insert a new RouteSegment join row.

        The caller (service) is responsible for validating that:
          - The route exists (non-deleted).
          - The segment exists (non-deleted).
          - The sequence_order is not already taken.
        """
        join_row = RouteSegment(
            route_id=route_id,
            segment_id=segment_id,
            sequence_order=sequence_order,
        )
        self._db.add(join_row)
        await self._db.flush()
        await self._db.refresh(join_row)
        logger.info(
            "RouteSegment added | route_id=%s | segment_id=%s | order=%d",
            route_id,
            segment_id,
            sequence_order,
        )
        return join_row

    async def remove_segment(
        self,
        route_id: uuid.UUID,
        segment_id: uuid.UUID,
    ) -> None:
        """
        Hard-delete the join row linking segment_id to route_id.

        This is a permanent removal — route_segments has no soft-delete.
        The caller (service) is responsible for verifying the join row exists.
        """
        await self._db.execute(
            delete(RouteSegment).where(
                RouteSegment.route_id == route_id,
                RouteSegment.segment_id == segment_id,
            )
        )
        await self._db.flush()
        logger.info(
            "RouteSegment removed | route_id=%s | segment_id=%s",
            route_id,
            segment_id,
        )
