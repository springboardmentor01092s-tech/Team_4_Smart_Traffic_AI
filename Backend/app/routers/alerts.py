"""
app/routers/alerts.py
"""
import uuid

from fastapi import APIRouter, Depends, Query, status

from app.dependencies.alerts import get_alert_service
from app.dependencies.auth import get_current_user, require_role
from app.dependencies.auth import get_current_user, require_role
from app.models.alert import AlertSeverity, AlertStatus, AlertType
from app.models.user import User, UserRole
from app.schemas.alert import AlertCreate, AlertRead, AlertUpdate
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["Traffic Alerts"])


@router.get(
    "",
    response_model=list[AlertRead],
    summary="List traffic alerts",
    dependencies=[Depends(get_current_user)],
)
async def list_alerts(
    segment_id: uuid.UUID | None = Query(default=None),
    status: AlertStatus | None = Query(default=None),
    severity: AlertSeverity | None = Query(default=None),
    alert_type: AlertType | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    service: AlertService = Depends(get_alert_service),
) -> list[AlertRead]:
    alerts = await service.list_alerts(
        segment_id=segment_id,
        status=status,
        severity=severity,
        alert_type=alert_type,
        skip=skip,
        limit=limit,
    )
    return [AlertRead.model_validate(a) for a in alerts]


@router.get(
    "/{alert_id}",
    response_model=AlertRead,
    summary="Get a traffic alert",
    dependencies=[Depends(get_current_user)],
)
async def get_alert(
    alert_id: uuid.UUID,
    service: AlertService = Depends(get_alert_service),
) -> AlertRead:
    alert = await service.get_alert(alert_id)
    return AlertRead.model_validate(alert)


@router.post(
    "",
    response_model=AlertRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a traffic alert",
)
async def create_alert(
    data: AlertCreate,
    service: AlertService = Depends(get_alert_service),
    current_user: User = Depends(require_role(UserRole.TRAFFIC_CONTROLLER, UserRole.ADMIN)),
) -> AlertRead:
    alert = await service.create_alert(data, created_by=current_user.id)
    return AlertRead.model_validate(alert)


@router.put(
    "/{alert_id}",
    response_model=AlertRead,
    summary="Update a traffic alert",
    dependencies=[Depends(require_role(UserRole.TRAFFIC_CONTROLLER, UserRole.ADMIN))],
)
async def update_alert(
    alert_id: uuid.UUID,
    data: AlertUpdate,
    service: AlertService = Depends(get_alert_service),
) -> AlertRead:
    alert = await service.update_alert(alert_id, data)
    return AlertRead.model_validate(alert)


@router.patch(
    "/{alert_id}/resolve",
    response_model=AlertRead,
    summary="Resolve a traffic alert",
    dependencies=[Depends(require_role(UserRole.TRAFFIC_CONTROLLER, UserRole.ADMIN))],
)
async def resolve_alert(
    alert_id: uuid.UUID,
    service: AlertService = Depends(get_alert_service),
) -> AlertRead:
    alert = await service.resolve_alert(alert_id)
    return AlertRead.model_validate(alert)


@router.patch(
    "/{alert_id}/dismiss",
    response_model=AlertRead,
    summary="Dismiss a traffic alert",
    dependencies=[Depends(require_role(UserRole.TRAFFIC_CONTROLLER, UserRole.ADMIN))],
)
async def dismiss_alert(
    alert_id: uuid.UUID,
    service: AlertService = Depends(get_alert_service),
) -> AlertRead:
    alert = await service.dismiss_alert(alert_id)
    return AlertRead.model_validate(alert)


@router.delete(
    "/{alert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a traffic alert",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_alert(
    alert_id: uuid.UUID,
    service: AlertService = Depends(get_alert_service),
) -> None:
    await service.delete_alert(alert_id)
