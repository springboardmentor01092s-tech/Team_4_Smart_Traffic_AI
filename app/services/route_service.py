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
  - NoViableRouteError: raised when no candidate routes can be scored.

Milestone 2 additions:
  estimate_travel_time(route_id) -> TravelTimeEstimateRead
    Calculates estimated route traversal time using current readings
    (speed_limit_kmh as fallback when no reading exists).

  compare_routes(route_ids) -> RouteComparisonRead
    Scores multiple candidate routes by travel time and congestion,
    returning a ranked list with the recommended route identified.

This service is HTTP-agnostic.  No FastAPI, no Request, no Response.
Dependencies are injected via the constructor and the DI factory
in app/dependencies/routes.py.
"""
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.core.exceptions import (
    NoViableRouteError,
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
    RouteComparisonItem,
    RouteComparisonRead,
    RouteCreate,
    RouteSegmentAdd,
    RouteTrafficRead,
    RouteUpdate,
    SegmentEstimateItem,
    SegmentTrafficItem,
    TravelTimeEstimateRead,
)

if TYPE_CHECKING:
    from app.repositories.prediction_repository import PredictionRepository

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

# Score penalty applied per congestion rank level during route comparison.
# A route with STANDSTILL adds 4 * 5 = 20 synthetic minutes to its score.
_CONGESTION_PENALTY_MINUTES_PER_RANK = 5.0


class RouteService:
    """
    Service for Route and RouteSegment business operations.

    Dependencies injected via constructor:
      - route_repo:      RouteRepository for all Route / RouteSegment DB access.
      - segment_repo:    SegmentRepository for segment existence validation.
      - reading_repo:    ReadingRepository for fetching latest readings.
      - prediction_repo: PredictionRepository (optional, for future predicted
                         congestion data; not yet used in scoring).
    """

    def __init__(
        self,
        route_repo: RouteRepository,
        segment_repo: SegmentRepository,
        reading_repo: ReadingRepository,
        prediction_repo: "PredictionRepository | None" = None,
    ) -> None:
        self._route_repo = route_repo
        self._segment_repo = segment_repo
        self._reading_repo = reading_repo
        self._prediction_repo = prediction_repo

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
        """
        routes = await self._route_repo.get_all(is_active=is_active, skip=skip, limit=limit)
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

        Algorithm (optimized batch execution):
          1. Fetch route (raises RouteNotFoundError if absent).
          2. Fetch ordered segment UUIDs from the join table.
          3. Batch-fetch latest readings for all segments in a single query.
          4. Compute worst_congestion_level using _CONGESTION_RANK dict.
          5. Assemble and return RouteTrafficRead.

        worst_congestion_level is None when no segment has any reading yet.
        """
        route = await self._route_repo.get_by_id(route_id)
        if route is None:
            raise RouteNotFoundError(route_id)

        segment_ids = await self._route_repo.get_segment_ids_for_route(route_id)
        readings_map = await self._reading_repo.get_latest_for_segments(segment_ids)

        segment_traffic_items: list[SegmentTrafficItem] = []
        segments_with_readings = 0
        worst_rank = -1
        worst_level: CongestionLevel | None = None

        for seg_id in segment_ids:
            reading = readings_map.get(seg_id)
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

    # ── Milestone 2: Travel-time estimation ───────────────────────────────────

    async def estimate_travel_time(self, route_id: uuid.UUID) -> TravelTimeEstimateRead:
        """
        Estimate total travel time for a route using current traffic readings.

        Algorithm (optimized batch execution):
          1. Fetch route (raises RouteNotFoundError if absent).
          2. Fetch ordered segment UUIDs from the join table.
          3. Batch-fetch segment models and latest readings in 2 queries total.
          4. For each segment in the route (ordered by sequence_order):
             - Use reading.average_speed_kmh when available and > 0.
             - Fall back to segment.speed_limit_kmh when no reading or speed <= 0.
             - travel_time_minutes = (length_km / speed_kmh) * 60.
          5. Sum segment times to produce estimated_travel_minutes.

        Worst congestion is tracked across all segments with readings.

        Args:
            route_id: UUID of the target route.

        Returns:
            TravelTimeEstimateRead with per-segment breakdown.

        Raises:
            RouteNotFoundError: If route does not exist.
        """
        route = await self._route_repo.get_by_id(route_id)
        if route is None:
            raise RouteNotFoundError(route_id)

        segment_ids = await self._route_repo.get_segment_ids_for_route(route_id)
        segments_map = await self._segment_repo.get_by_ids(segment_ids)
        readings_map = await self._reading_repo.get_latest_for_segments(segment_ids)

        total_minutes = 0.0
        segments_with_readings = 0
        worst_rank = -1
        worst_level: CongestionLevel | None = None
        segment_estimates: list[SegmentEstimateItem] = []

        for seg_id in segment_ids:
            segment = segments_map.get(seg_id)
            if segment is None:
                # Segment was soft-deleted after being added to route; skip.
                logger.warning(
                    "estimate_travel_time: segment %s not found, skipping.", seg_id
                )
                continue

            reading = readings_map.get(seg_id)

            if reading is not None and reading.average_speed_kmh > 0:
                speed_kmh = float(reading.average_speed_kmh)
                data_source = "reading"
                segments_with_readings += 1

                rank = _CONGESTION_RANK.get(reading.congestion_level, -1)
                if rank > worst_rank:
                    worst_rank = rank
                    worst_level = reading.congestion_level
            else:
                speed_kmh = float(segment.speed_limit_kmh)
                data_source = "speed_limit"
                if speed_kmh <= 0:
                    speed_kmh = 50.0  # absolute fallback

            seg_minutes = (segment.length_km / speed_kmh) * 60.0
            total_minutes += seg_minutes

            segment_estimates.append(
                SegmentEstimateItem(
                    segment_id=seg_id,
                    segment_name=segment.name,
                    length_km=segment.length_km,
                    speed_used_kmh=round(speed_kmh, 2),
                    estimated_minutes=round(seg_minutes, 2),
                    data_source=data_source,
                )
            )

        return TravelTimeEstimateRead(
            route_id=route_id,
            route_name=route.name,
            total_distance_km=route.total_distance_km,
            estimated_travel_minutes=round(total_minutes, 2),
            worst_congestion_level=worst_level,
            segments_with_readings=segments_with_readings,
            segment_count=len(segment_ids),
            segment_estimates=segment_estimates,
        )

    # ── Milestone 2: Route comparison / recommendation ────────────────────────

    async def compare_routes(self, route_ids: list[uuid.UUID]) -> RouteComparisonRead:
        """
        Score and rank candidate routes, returning the recommended route.

        Scoring algorithm (lower is better):
          score = estimated_travel_minutes + (worst_congestion_rank * PENALTY)

        Where PENALTY = _CONGESTION_PENALTY_MINUTES_PER_RANK = 5 minutes.

        For example, a route with HEAVY congestion (rank=3) and
        60 estimated minutes scores: 60 + 3*5 = 75.

        Routes without any readings are scored using speed_limit_kmh only,
        with no congestion penalty (rank=-1 treated as 0).

        The route with the lowest score is recommended.
        All input route_ids are evaluated; invalid IDs are silently skipped.

        Args:
            route_ids: List of candidate route UUIDs to compare.

        Returns:
            RouteComparisonRead with ranked list and recommended route.

        Raises:
            NoViableRouteError: If no valid routes could be scored.
        """
        scored: list[tuple[float, TravelTimeEstimateRead, uuid.UUID]] = []

        for route_id in route_ids:
            try:
                estimate = await self.estimate_travel_time(route_id)
            except RouteNotFoundError:
                logger.warning("compare_routes: route %s not found, skipping.", route_id)
                continue

            worst_rank = _CONGESTION_RANK.get(estimate.worst_congestion_level, -1) \
                if estimate.worst_congestion_level else -1
            congestion_penalty = max(0, worst_rank) * _CONGESTION_PENALTY_MINUTES_PER_RANK
            score = estimate.estimated_travel_minutes + congestion_penalty
            scored.append((score, estimate, route_id))

        if not scored:
            raise NoViableRouteError()

        # Sort ascending by score (lower = better)
        scored.sort(key=lambda t: t[0])

        best_route_id = scored[0][2]
        best_score = scored[0][0]

        # Fetch routes for name/origin/destination metadata in batch
        valid_route_ids = [r_id for _, _, r_id in scored]
        routes_map = await self._route_repo.get_by_ids(valid_route_ids)

        comparison_items: list[RouteComparisonItem] = []
        for rank_idx, (score, estimate, route_id) in enumerate(scored, start=1):
            is_recommended = route_id == best_route_id
            if is_recommended:
                reason = (
                    f"Lowest estimated travel time ({estimate.estimated_travel_minutes:.1f} min) "
                    f"with best congestion score."
                )
            else:
                delay = score - best_score
                reason = (
                    f"Estimated {delay:.1f} additional minutes vs recommended route "
                    f"(travel: {estimate.estimated_travel_minutes:.1f} min, "
                    f"congestion: {estimate.worst_congestion_level.value if estimate.worst_congestion_level else 'N/A'})."
                )

            route = routes_map.get(route_id)

            comparison_items.append(
                RouteComparisonItem(
                    route_id=route_id,
                    route_name=estimate.route_name,
                    origin_name=route.origin_name if route else "",
                    destination_name=route.destination_name if route else "",
                    total_distance_km=estimate.total_distance_km,
                    estimated_travel_minutes=estimate.estimated_travel_minutes,
                    worst_congestion_level=estimate.worst_congestion_level,
                    segments_with_readings=estimate.segments_with_readings,
                    segment_count=estimate.segment_count,
                    rank=rank_idx,
                    is_recommended=is_recommended,
                    recommendation_reason=reason,
                )
            )

        return RouteComparisonRead(
            recommended_route_id=best_route_id,
            routes=comparison_items,
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
        """
        route = await self._route_repo.get_by_id(route_id)
        if route is None:
            raise RouteNotFoundError(route_id)

        update_fields: dict[str, object] = data.model_dump(exclude_unset=True)

        if not update_fields:
            logger.debug("update_route no-op | id=%s", route_id)
            return route

        update_fields["updated_at"] = datetime.now(UTC)
        updated = await self._route_repo.update(route, **update_fields)
        return updated

    async def add_segment_to_route(
        self,
        route_id: uuid.UUID,
        data: RouteSegmentAdd,
    ) -> RouteSegment:
        """
        Add a traffic segment to a route at a specific sequence position.
        """
        route = await self._route_repo.get_by_id(route_id)
        if route is None:
            raise RouteNotFoundError(route_id)

        segment = await self._segment_repo.get_by_id(data.segment_id)
        if segment is None:
            raise SegmentNotFoundError(data.segment_id)

        taken = await self._route_repo.check_sequence_order_taken(route_id, data.sequence_order)
        if taken:
            raise RouteSequenceConflictError(route_id, data.sequence_order)

        join_row = await self._route_repo.add_segment(
            route_id=route_id,
            segment_id=data.segment_id,
            sequence_order=data.sequence_order,
        )
        return join_row

    async def remove_segment_from_route(
        self,
        route_id: uuid.UUID,
        segment_id: uuid.UUID,
    ) -> None:
        """
        Remove a segment from a route (hard-deletes the join row).
        """
        route = await self._route_repo.get_by_id(route_id)
        if route is None:
            raise RouteNotFoundError(route_id)

        join_row = await self._route_repo.get_route_segment(route_id, segment_id)
        if join_row is None:
            raise SegmentNotInRouteError(route_id, segment_id)

        await self._route_repo.remove_segment(route_id, segment_id)

    async def delete_route(self, route_id: uuid.UUID) -> None:
        """
        Soft-delete a route.
        """
        route = await self._route_repo.get_by_id(route_id)
        if route is None:
            raise RouteNotFoundError(route_id)

        await self._route_repo.soft_delete(route)
        logger.warning("Route soft-deleted | id=%s | name=%r", route_id, route.name)
