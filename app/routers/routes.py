"""
app/routers/routes.py

Thin REST API router for the Routes module.

Milestone 2 additions:
  GET /compare?route_ids=...     -> compare_routes  [PUB auth]
  GET /{route_id}/estimate       -> get_travel_time_estimate  [PUB auth]

All handlers: extract params -> call one service method -> return schema.
No business logic. No try/except for domain exceptions (caught globally).
RBAC: read endpoints require authentication (PUB); write endpoints require ADMIN.
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.dependencies.auth import get_current_user, require_role
from app.dependencies.routes import get_route_service
from app.models.user import User, UserRole
from app.schemas.route import (
    RouteComparisonRead,
    RouteCreate,
    RouteDetailRead,
    RouteRead,
    RouteSegmentAdd,
    RouteSegmentRead,
    RouteTrafficRead,
    RouteUpdate,
    TravelTimeEstimateRead,
)
from app.services.route_service import RouteService

router = APIRouter(prefix="/routes", tags=["Routes"])


@router.get(
    "/compare",
    response_model=RouteComparisonRead,
    summary="Compare multiple routes and get a recommendation",
)
async def compare_routes(
    route_ids: Annotated[
        list[uuid.UUID],
        Query(description="Comma-separated list of route UUIDs to compare (min 1)"),
    ],
    service: RouteService = Depends(get_route_service),
    current_user: User = Depends(get_current_user),
) -> RouteComparisonRead:
    """
    Score and rank candidate routes by estimated travel time and congestion.

    Returns a ranked list with the recommended route identified.
    Scoring: estimated_travel_minutes + (congestion_rank * 5 min penalty).
    """
    return await service.compare_routes(route_ids)


@router.get(
    "",
    response_model=list[RouteRead],
    summary="List routes",
)
async def list_routes(
    is_active: bool | None = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    service: RouteService = Depends(get_route_service),
    current_user: User = Depends(get_current_user),
) -> list[RouteRead]:
    """Return a paginated list of non-deleted routes."""
    return await service.list_routes(is_active=is_active, skip=skip, limit=limit)


@router.get(
    "/{route_id}/traffic",
    response_model=RouteTrafficRead,
    summary="Get route traffic status",
)
async def get_route_traffic(
    route_id: uuid.UUID,
    service: RouteService = Depends(get_route_service),
    current_user: User = Depends(get_current_user),
) -> RouteTrafficRead:
    """
    Return aggregated current traffic across all segments of a route.

    worst_congestion_level uses severity ordering:
    STANDSTILL > HEAVY > MODERATE > LIGHT > FREE_FLOW.
    Returns None when no segment has readings yet.
    """
    return await service.get_route_traffic(route_id)


@router.get(
    "/{route_id}/estimate",
    response_model=TravelTimeEstimateRead,
    summary="Estimate travel time for a route",
)
async def get_travel_time_estimate(
    route_id: uuid.UUID,
    service: RouteService = Depends(get_route_service),
    current_user: User = Depends(get_current_user),
) -> TravelTimeEstimateRead:
    """
    Estimate traversal time for a route using current traffic readings.

    Uses actual average_speed_kmh from the latest reading per segment.
    Falls back to speed_limit_kmh when no reading is available.
    Returns per-segment breakdown with data source indicated.
    """
    return await service.estimate_travel_time(route_id)


@router.get(
    "/{route_id}",
    response_model=RouteDetailRead,
    summary="Get route by ID",
)
async def get_route(
    route_id: uuid.UUID,
    service: RouteService = Depends(get_route_service),
    current_user: User = Depends(get_current_user),
) -> RouteDetailRead:
    """Fetch a single route with its ordered segment list."""
    return await service.get_route(route_id)


@router.post(
    "",
    response_model=RouteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a route",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def create_route(
    data: RouteCreate,
    service: RouteService = Depends(get_route_service),
) -> RouteRead:
    """Create a new named route. Requires ADMIN role."""
    return await service.create_route(data)


@router.put(
    "/{route_id}",
    response_model=RouteRead,
    summary="Update a route",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def update_route(
    route_id: uuid.UUID,
    data: RouteUpdate,
    service: RouteService = Depends(get_route_service),
) -> RouteRead:
    """Partially update a route metadata. Requires ADMIN role."""
    return await service.update_route(route_id, data)


@router.post(
    "/{route_id}/segments",
    response_model=RouteSegmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add segment to route",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def add_segment_to_route(
    route_id: uuid.UUID,
    data: RouteSegmentAdd,
    service: RouteService = Depends(get_route_service),
) -> RouteSegmentRead:
    """Add a traffic segment to a route at a specific sequence position. Requires ADMIN."""
    return await service.add_segment_to_route(route_id, data)


@router.delete(
    "/{route_id}/segments/{segment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove segment from route",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def remove_segment_from_route(
    route_id: uuid.UUID,
    segment_id: uuid.UUID,
    service: RouteService = Depends(get_route_service),
) -> None:
    """Remove a segment from a route (hard-deletes the join row). Requires ADMIN."""
    await service.remove_segment_from_route(route_id, segment_id)


@router.delete(
    "/{route_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a route",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_route(
    route_id: uuid.UUID,
    service: RouteService = Depends(get_route_service),
) -> None:
    """Soft-delete a route (sets deleted_at). Requires ADMIN."""
    await service.delete_route(route_id)
