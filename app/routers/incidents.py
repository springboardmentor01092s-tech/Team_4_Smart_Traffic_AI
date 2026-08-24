"""
app/routers/incidents.py

FastAPI router for Incident Ingestion endpoints.
"""
from fastapi import APIRouter, Depends, status

from app.dependencies.auth import require_role
from app.dependencies.incidents import get_incident_service
from app.models.user import User, UserRole
from app.schemas.incident import IncidentCreate
from app.services.incident_service import IncidentService

router = APIRouter(
    prefix="/incidents",
    tags=["Incidents"],
    # Incidents can only be reported by ADMIN or TRAFFIC_CONTROLLER
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.TRAFFIC_CONTROLLER))],
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Report a new traffic incident",
)
async def report_incident(
    data: IncidentCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.TRAFFIC_CONTROLLER)),
    incident_service: IncidentService = Depends(get_incident_service),
) -> dict:
    """
    Submit a manual incident report (e.g., accident, road closure).
    Idempotent: updates existing active alert of the same type on the given segment if it exists.
    """
    await incident_service.report_incident(data, current_user)
    return {"status": "success", "message": "Incident processed"}
