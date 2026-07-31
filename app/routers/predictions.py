import uuid
from typing import Sequence

from fastapi import APIRouter, Depends, Query, status

from app.dependencies.auth import get_current_user, require_role
from app.dependencies.predictions import get_prediction_service
from app.models.prediction import PredictionStatus
from app.models.user import User, UserRole
from app.schemas.prediction import PredictionComplete, PredictionCreate, PredictionRead
from app.services.prediction_service import PredictionService

router = APIRouter(prefix="/predictions", tags=["Traffic Predictions"])


@router.get(
    "/",
    response_model=list[PredictionRead],
    summary="List predictions",
)
async def list_predictions(
    segment_id: uuid.UUID | None = Query(None, description="Filter by segment"),
    status: PredictionStatus | None = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: PredictionService = Depends(get_prediction_service),
    current_user: User = Depends(get_current_user),  # Authentication required (PUB)
) -> Sequence[PredictionRead]:
    """Retrieve a list of traffic predictions."""
    return await service.list_predictions(
        segment_id=segment_id, status=status, skip=skip, limit=limit
    )


@router.get(
    "/{prediction_id}",
    response_model=PredictionRead,
    summary="Get a prediction by ID",
)
async def get_prediction(
    prediction_id: uuid.UUID,
    service: PredictionService = Depends(get_prediction_service),
    current_user: User = Depends(get_current_user),  # PUB
) -> PredictionRead:
    """Fetch a single traffic prediction."""
    return await service.get_prediction(prediction_id)


@router.get(
    "/segment/{segment_id}/upcoming",
    response_model=list[PredictionRead],
    summary="Get upcoming predictions for a segment",
)
async def get_upcoming_for_segment(
    segment_id: uuid.UUID,
    service: PredictionService = Depends(get_prediction_service),
    current_user: User = Depends(get_current_user),  # PUB
) -> Sequence[PredictionRead]:
    """Fetch upcoming PENDING/COMPLETED predictions for a segment."""
    return await service.get_upcoming_for_segment(segment_id)


@router.post(
    "/",
    response_model=PredictionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new prediction",
    dependencies=[Depends(require_role(UserRole.TRAFFIC_CONTROLLER, UserRole.ADMIN))],
)
async def create_prediction(
    data: PredictionCreate,
    service: PredictionService = Depends(get_prediction_service),
) -> PredictionRead:
    """Request a new traffic prediction."""
    return await service.create_prediction(data)


@router.patch(
    "/{prediction_id}/complete",
    response_model=PredictionRead,
    summary="Complete a prediction",
    dependencies=[Depends(require_role(UserRole.TRAFFIC_CONTROLLER, UserRole.ADMIN))],
)
async def complete_prediction(
    prediction_id: uuid.UUID,
    data: PredictionComplete,
    service: PredictionService = Depends(get_prediction_service),
) -> PredictionRead:
    """Submit the result of a traffic prediction model."""
    return await service.complete_prediction(prediction_id, data)


@router.patch(
    "/{prediction_id}/fail",
    response_model=PredictionRead,
    summary="Fail a prediction",
    dependencies=[Depends(require_role(UserRole.TRAFFIC_CONTROLLER, UserRole.ADMIN))],
)
async def fail_prediction(
    prediction_id: uuid.UUID,
    service: PredictionService = Depends(get_prediction_service),
) -> PredictionRead:
    """Mark a pending prediction as FAILED."""
    return await service.fail_prediction(prediction_id)


@router.delete(
    "/{prediction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a prediction",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_prediction(
    prediction_id: uuid.UUID,
    service: PredictionService = Depends(get_prediction_service),
) -> None:
    """Soft-delete a prediction (Admin only)."""
    await service.delete_prediction(prediction_id)
