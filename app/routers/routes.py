"""
app/routers/routes.py

Thin REST API router for the Routes module.

Design rules followed:
  - Each handler: extract params → call one service method → return schema.
  - No business logic. No try/except for domain exceptions (caught globally).
  - Root-level paths use "" (not "/") to prevent 307 redirects in FastAPI.
  - RBAC: read endpoints require authentication (PUB); all write endpoints
    require ADMIN role, consistent with the camera and segment routers.

Endpoints:
  GET    ""                          → list_routes
  GET    "/{route_id}"               → get_route (with segments)
  GET    "/{route_id}/traffic"       → get_route_traffic
  POST   ""                          → create_route  [ADMIN]
  PUT    "/{route_id}"               → update_route  [ADMIN]
  POST   "/{route_id}/segments"      → add_segment   [ADMIN]
  DELETE "/{route_id}/segments/{id}" → remove_segment [ADMIN]
  DELETE "/{route_id}"               → delete_route  [ADMIN]
"""
import uuid

from fastapi import APIRouter, Depends, Query, status

from app.dependencies.auth import get_current_user, require_role
from app.dependencies.routes import get_route_service
from app.models.user import User, UserRole
from app.schemas.route import (
    RouteCreate,
    RouteDetailRead,
    RouteRead,
    RouteSegmentAdd,
    RouteSegmentRead,
    RouteTrafficRead,
    RouteUpdate,
)
from app.services.route_service import RouteService

router = APIRouter(prefix="/routes", tags=["Routes"])


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

    Computed worst_congestion_level uses severity ordering:
    STANDSTILL > HEAVY > MODERATE > LIGHT > FREE_FLOW.
    Returns None when no segment has readings yet.
    """
    return await service.get_route_traffic(route_id)


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
    """Partially update a route's metadata. Requires ADMIN role."""
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
