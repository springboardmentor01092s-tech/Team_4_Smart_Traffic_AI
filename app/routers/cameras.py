"""
app/routers/cameras.py

HTTP routes for the Traffic Cameras module.

Routes:
    GET    /api/v1/cameras              — List cameras (any authenticated user)
    GET    /api/v1/cameras/{camera_id}  — Get camera detail (any authenticated user)
    POST   /api/v1/cameras              — Create camera (ADMIN only)
    PUT    /api/v1/cameras/{camera_id}  — Update camera (ADMIN only)
    DELETE /api/v1/cameras/{camera_id}  — Soft-delete camera (ADMIN only)

Router rules (enforced strictly):
  - Each handler does exactly three things: extract params, call service, return schema.
  - No try/except for domain errors — those are caught by global handlers.
  - No business logic in this file.
"""
import uuid

from fastapi import APIRouter, Depends, Query, status

from app.dependencies.auth import get_current_user, require_role
from app.dependencies.cameras import get_camera_service
from app.models.camera import CameraStatus
from app.models.user import UserRole
from app.schemas.camera import CameraCreate, CameraRead, CameraUpdate
from app.services.camera_service import CameraService

router = APIRouter(prefix="/cameras", tags=["Traffic Cameras"])


@router.get(
    "",
    response_model=list[CameraRead],
    summary="List traffic cameras",
    description=(
        "Return a paginated list of non-deleted traffic cameras. "
        "Optionally filter by status. Requires authentication."
    ),
    dependencies=[Depends(get_current_user)],
)
async def list_cameras(
    status: CameraStatus | None = Query(
        default=None,
        description="Filter cameras by operational status.",
    ),
    skip: int = Query(default=0, ge=0, description="Pagination offset."),
    limit: int = Query(default=100, ge=1, le=500, description="Max items to return."),
    service: CameraService = Depends(get_camera_service),
) -> list[CameraRead]:
    cameras = await service.list_cameras(status=status, skip=skip, limit=limit)
    return [CameraRead.model_validate(c) for c in cameras]


@router.get(
    "/{camera_id}",
    response_model=CameraRead,
    summary="Get a traffic camera",
    description=(
        "Return a single traffic camera by UUID. "
        "Returns 404 if the camera does not exist or has been deleted. "
        "Requires authentication."
    ),
    dependencies=[Depends(get_current_user)],
)
async def get_camera(
    camera_id: uuid.UUID,
    service: CameraService = Depends(get_camera_service),
) -> CameraRead:
    camera = await service.get_camera(camera_id)
    return CameraRead.model_validate(camera)


@router.post(
    "",
    response_model=CameraRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a traffic camera",
    description=(
        "Create a new traffic camera. "
        "Requires ADMIN role."
    ),
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def create_camera(
    data: CameraCreate,
    service: CameraService = Depends(get_camera_service),
) -> CameraRead:
    camera = await service.create_camera(data)
    return CameraRead.model_validate(camera)


@router.put(
    "/{camera_id}",
    response_model=CameraRead,
    summary="Update a traffic camera",
    description=(
        "Partially update a traffic camera. Only provided fields are changed. "
        "Returns 404 if the camera does not exist or has been deleted. "
        "Requires ADMIN role."
    ),
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def update_camera(
    camera_id: uuid.UUID,
    data: CameraUpdate,
    service: CameraService = Depends(get_camera_service),
) -> CameraRead:
    camera = await service.update_camera(camera_id, data)
    return CameraRead.model_validate(camera)


@router.delete(
    "/{camera_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a traffic camera",
    description=(
        "Soft-delete a traffic camera. The record is retained in the database "
        "but is no longer returned by any endpoint. "
        "Returns 409 if the camera is assigned to active road segments. "
        "Requires ADMIN role."
    ),
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_camera(
    camera_id: uuid.UUID,
    service: CameraService = Depends(get_camera_service),
) -> None:
    await service.delete_camera(camera_id)
