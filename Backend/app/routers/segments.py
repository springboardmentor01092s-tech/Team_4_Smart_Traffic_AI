"""
app/routers/segments.py
"""
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, status

from app.dependencies.auth import get_current_user, require_role
from app.dependencies.segments import get_segment_service
from app.models.segment import SegmentStatus
from app.models.user import UserRole
from app.schemas.reading import ReadingRead
from app.schemas.segment import SegmentCreate, SegmentRead, SegmentUpdate
from app.services.segment_service import SegmentService

router = APIRouter(prefix="/segments", tags=["Traffic Segments"])


@router.get(
    "",
    response_model=list[SegmentRead],
    summary="List traffic segments",
    dependencies=[Depends(get_current_user)],
)
async def list_segments(
    status: SegmentStatus | None = Query(default=None),
    camera_id: uuid.UUID | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    service: SegmentService = Depends(get_segment_service),
) -> list[SegmentRead]:
    segments = await service.list_segments(status=status, camera_id=camera_id, skip=skip, limit=limit)
    return [SegmentRead.model_validate(s) for s in segments]


@router.get(
    "/{segment_id}",
    response_model=SegmentRead,
    summary="Get a traffic segment",
    dependencies=[Depends(get_current_user)],
)
async def get_segment(
    segment_id: uuid.UUID,
    service: SegmentService = Depends(get_segment_service),
) -> SegmentRead:
    segment = await service.get_segment(segment_id)
    return SegmentRead.model_validate(segment)


@router.get(
    "/{segment_id}/latest-reading",
    response_model=ReadingRead | None,
    summary="Get most recent reading for segment",
    dependencies=[Depends(get_current_user)],
)
async def get_latest_reading(
    segment_id: uuid.UUID,
    service: SegmentService = Depends(get_segment_service),
) -> Any:
    return await service.get_latest_reading(segment_id)


@router.post(
    "",
    response_model=SegmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a traffic segment",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def create_segment(
    data: SegmentCreate,
    service: SegmentService = Depends(get_segment_service),
) -> SegmentRead:
    segment = await service.create_segment(data)
    return SegmentRead.model_validate(segment)


@router.put(
    "/{segment_id}",
    response_model=SegmentRead,
    summary="Update a traffic segment",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def update_segment(
    segment_id: uuid.UUID,
    data: SegmentUpdate,
    service: SegmentService = Depends(get_segment_service),
) -> SegmentRead:
    segment = await service.update_segment(segment_id, data)
    return SegmentRead.model_validate(segment)


@router.delete(
    "/{segment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a traffic segment",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_segment(
    segment_id: uuid.UUID,
    service: SegmentService = Depends(get_segment_service),
) -> None:
    await service.delete_segment(segment_id)
