"""
app/services/route_service.py

Business logic layer for the Routes module.

RouteService owns all domain rules:
  - RouteNotFoundError: raised when a route UUID resolves to nothing.
  - SegmentNotFoundError (re-used): raised when a segment UUID is invalid
    during add_segment_to_route.
  - RouteSequenceConflictError: raised when sequence_order is already
    occupied in the route.
  - SegmentNotInRouteError: raised when trying to remove a segment that
    is not part of the route.

This service is HTTP-agnostic.  No FastAPI, no Request, no Response.
Dependencies are injected via the constructor and the DI factory
in app/dependencies/routes.py.

CongestionLevel severity ranking used by get_route_traffic:
  STANDSTILL=4 > HEAVY=3 > MODERATE=2 > LIGHT=1 > FREE_FLOW=0
  worst_congestion_level is None if no segment has any reading.
"""
import uuid
from datetime import UTC, datetime

from app.core.exceptions import (
    RouteNotFoundError,
    RouteSequenceConflictError,
    SegmentNotFoundError,
    SegmentNotInRouteError,
)
from app.core.logging import get_logger
from app.models.route import Route, RouteSegment
from app.models.segment import CongestionLevel
from app.repositories.reading_repository import ReadingRepository
from app.repositories.route_repository import RouteRepository
from app.repositories.segment_repository import SegmentRepository
from app.schemas.route import (
    RouteCreate,
    RouteSegmentAdd,
    RouteTrafficRead,
    RouteUpdate,
    SegmentTrafficItem,
)

logger = get_logger(__name__)

# Explicit severity ranking for CongestionLevel comparison.
# Higher value = worse congestion.
_CONGESTION_RANK: dict[CongestionLevel, int] = {
    CongestionLevel.FREE_FLOW: 0,
    CongestionLevel.LIGHT: 1,
    CongestionLevel.MODERATE: 2,
    CongestionLevel.HEAVY: 3,
    CongestionLevel.STANDSTILL: 4,
}


class RouteService:
    """
    Service for Route and RouteSegment business operations.

    Dependencies injected via constructor:
      - route_repo:   RouteRepository for all Route / RouteSegment DB access.
      - segment_repo: SegmentRepository for segment existence validation.
      - reading_repo: ReadingRepository for fetching latest readings in
                      get_route_traffic.
    """

    def __init__(
        self,
        route_repo: RouteRepository,
        segment_repo: SegmentRepository,
        reading_repo: ReadingRepository,
    ) -> None:
        self._route_repo = route_repo
        self._segment_repo = segment_repo
        self._reading_repo = reading_repo

    # ── Read operations ───────────────────────────────────────────────────────

    async def list_routes(
        self,
        *,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Route]:
        """
        Return a paginated, non-deleted list of routes.

        Args:
            is_active: If provided, only routes matching this flag are returned.
            skip:      Pagination offset.
            limit:     Maximum items per page.
        """
        routes = await self._route_repo.get_all(is_active=is_active, skip=skip, limit=limit)
        logger.debug(
            "list_routes | is_active=%s | skip=%d | limit=%d | returned=%d",
            is_active,
            skip,
            limit,
            len(routes),
        )
        return list(routes)

    async def get_route(self, route_id: uuid.UUID) -> Route:
        """
        Return a route by UUID with its route_segments eagerly loaded.

        Raises:
            RouteNotFoundError: If no non-deleted route with this UUID exists.
        """
        route = await self._route_repo.get_by_id_with_segments(route_id)
        if route is None:
            raise RouteNotFoundError(route_id)
        return route

    async def get_route_traffic(self, route_id: uuid.UUID) -> RouteTrafficRead:
        """
        Return the aggregated current traffic status across all segments of a route.

        Algorithm:
          1. Fetch route (raises RouteNotFoundError if absent).
          2. Fetch ordered segment UUIDs from the join table.
          3. For each segment UUID, fetch the latest reading.
          4. Compute worst_congestion_level using _CONGESTION_RANK dict.
          5. Assemble and return RouteTrafficRead.

        worst_congestion_level is None when no segment has any reading yet.
        """
        route = await self._route_repo.get_by_id(route_id)
        if route is None:
            raise RouteNotFoundError(route_id)

        segment_ids = await self._route_repo.get_segment_ids_for_route(route_id)

        segment_traffic_items: list[SegmentTrafficItem] = []
        segments_with_readings = 0
        worst_rank = -1
        worst_level: CongestionLevel | None = None

        for seg_id in segment_ids:
            reading = await self._reading_repo.get_latest_for_segment(seg_id)
            if reading is not None:
                segments_with_readings += 1
                rank = _CONGESTION_RANK.get(reading.congestion_level, -1)
                if rank > worst_rank:
                    worst_rank = rank
                    worst_level = reading.congestion_level
                segment_traffic_items.append(
                    SegmentTrafficItem(
                        segment_id=seg_id,
                        congestion_level=reading.congestion_level,
                        vehicle_count=reading.vehicle_count,
                        average_speed_kmh=reading.average_speed_kmh,
                        recorded_at=reading.recorded_at,
                    )
                )
            else:
                segment_traffic_items.append(
                    SegmentTrafficItem(
                        segment_id=seg_id,
                        congestion_level=None,
                        vehicle_count=None,
                        average_speed_kmh=None,
                        recorded_at=None,
                    )
                )

        return RouteTrafficRead(
            route_id=route_id,
            route_name=route.name,
            worst_congestion_level=worst_level,
            segment_count=len(segment_ids),
            segments_with_readings=segments_with_readings,
            segment_traffic=segment_traffic_items,
        )

    # ── Write operations ──────────────────────────────────────────────────────

    async def create_route(self, data: RouteCreate) -> Route:
        """
        Create and persist a new Route.

        Pydantic's Field(gt=0) on total_distance_km already prevents
        zero/negative values at the schema layer; no additional service check.
        """
        route = await self._route_repo.create(
            name=data.name,
            origin_name=data.origin_name,
            destination_name=data.destination_name,
            total_distance_km=data.total_distance_km,
        )
        logger.info("Route created | id=%s | name=%r", route.id, route.name)
        return route

    async def update_route(
        self,
        route_id: uuid.UUID,
        data: RouteUpdate,
    ) -> Route:
        """
        Apply a partial update to an existing route.

        Only fields that are explicitly present in `data` are applied.
        Uses RouteUpdate.model_dump(exclude_unset=True) to distinguish between
        'field not sent' and 'field sent as None'.

        Raises:
            RouteNotFoundError: If the route does not exist or is soft-deleted.
        """
        route = await self._route_repo.get_by_id(route_id)
        if route is None:
            raise RouteNotFoundError(route_id)

        # Use exclude_unset to only apply fields the caller explicitly provided.
        update_fields: dict[str, object] = data.model_dump(exclude_unset=True)

        if not update_fields:
            # No fields to update — return unchanged route.
            logger.debug("update_route no-op | id=%s", route_id)
            return route

        update_fields["updated_at"] = datetime.now(UTC)
        updated = await self._route_repo.update(route, **update_fields)
        logger.info(
            "Route updated | id=%s | fields=%s",
            route_id,
            [k for k in update_fields if k != "updated_at"],
        )
        return updated

    async def add_segment_to_route(
        self,
        route_id: uuid.UUID,
        data: RouteSegmentAdd,
    ) -> RouteSegment:
        """
        Add a traffic segment to a route at a specific sequence position.

        Business rules:
          1. Route must exist and not be soft-deleted.
          2. Segment must exist and not be soft-deleted.
          3. sequence_order must not already be taken in this route.

        Raises:
            RouteNotFoundError:         Rule 1 violation.
            SegmentNotFoundError:       Rule 2 violation.
            RouteSequenceConflictError: Rule 3 violation.
        """
        # Rule 1: route must exist.
        route = await self._route_repo.get_by_id(route_id)
        if route is None:
            raise RouteNotFoundError(route_id)

        # Rule 2: segment must exist.
        segment = await self._segment_repo.get_by_id(data.segment_id)
        if segment is None:
            raise SegmentNotFoundError(data.segment_id)

        # Rule 3: sequence_order must not be taken.
        taken = await self._route_repo.check_sequence_order_taken(route_id, data.sequence_order)
        if taken:
            raise RouteSequenceConflictError(route_id, data.sequence_order)

        join_row = await self._route_repo.add_segment(
            route_id=route_id,
            segment_id=data.segment_id,
            sequence_order=data.sequence_order,
        )
        logger.info(
            "Segment added to route | route_id=%s | segment_id=%s | order=%d",
            route_id,
            data.segment_id,
            data.sequence_order,
        )
        return join_row

    async def remove_segment_from_route(
        self,
        route_id: uuid.UUID,
        segment_id: uuid.UUID,
    ) -> None:
        """
        Remove a segment from a route (hard-deletes the join row).

        Business rules:
          1. Route must exist and not be soft-deleted.
          2. The join row (route_id, segment_id) must exist.

        Raises:
            RouteNotFoundError:     Rule 1 violation.
            SegmentNotInRouteError: Rule 2 violation.
        """
        route = await self._route_repo.get_by_id(route_id)
        if route is None:
            raise RouteNotFoundError(route_id)

        join_row = await self._route_repo.get_route_segment(route_id, segment_id)
        if join_row is None:
            raise SegmentNotInRouteError(route_id, segment_id)

        await self._route_repo.remove_segment(route_id, segment_id)
        logger.info(
            "Segment removed from route | route_id=%s | segment_id=%s",
            route_id,
            segment_id,
        )

    async def delete_route(self, route_id: uuid.UUID) -> None:
        """
        Soft-delete a route.

        Sets deleted_at on the route. The route_segments join rows remain
        in place and are cleaned up on any physical purge via ON DELETE CASCADE.

        Raises:
            RouteNotFoundError: If route does not exist or is already deleted.
        """
        route = await self._route_repo.get_by_id(route_id)
        if route is None:
            raise RouteNotFoundError(route_id)

        await self._route_repo.soft_delete(route)
        logger.warning("Route soft-deleted | id=%s | name=%r", route_id, route.name)
