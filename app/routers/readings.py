import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status

from app.dependencies.auth import require_role
from app.dependencies.readings import get_reading_service
from app.models.segment import CongestionLevel
from app.models.user import UserRole
from app.schemas.reading import ReadingCreate, ReadingRead
from app.services.reading_service import ReadingService


router = APIRouter(prefix="/readings", tags=["Traffic Readings"])


@router.post(
    "",
    response_model=ReadingRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.TRAFFIC_CONTROLLER, UserRole.ADMIN))],
)
async def submit_reading(
    data: ReadingCreate,
    service: ReadingService = Depends(get_reading_service),
) -> dict:
    """Submit a new traffic reading for a segment."""
    reading = await service.submit_reading(data)
    # Pydantic v2 requires returning object or dict matching schema.
    # We can return the SQLAlchemy model since from_attributes=True is set.
    return reading  # type: ignore


@router.get(
    "",
    response_model=list[ReadingRead],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.PUBLIC_USER, UserRole.TRAFFIC_CONTROLLER, UserRole.ADMIN))],
)
async def list_readings(
    segment_id: uuid.UUID | None = Query(None, description="Filter by segment ID"),
    from_dt: datetime | None = Query(None, description="Start date/time"),
    to_dt: datetime | None = Query(None, description="End date/time"),
    congestion_level: CongestionLevel | None = Query(None, description="Filter by congestion level"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: ReadingService = Depends(get_reading_service),
) -> list:
    """List traffic readings with optional filtering."""
    readings = await service.list_readings(
        segment_id=segment_id,
        from_dt=from_dt,
        to_dt=to_dt,
        congestion_level=congestion_level,
        skip=skip,
        limit=limit,
    )
    return list(readings)


@router.get(
    "/{reading_id}",
    response_model=ReadingRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.PUBLIC_USER, UserRole.TRAFFIC_CONTROLLER, UserRole.ADMIN))],
)
async def get_reading(
    reading_id: int,
    service: ReadingService = Depends(get_reading_service),
) -> dict:
    """Get a specific traffic reading by ID."""
    reading = await service.get_reading(reading_id)
    return reading  # type: ignore
