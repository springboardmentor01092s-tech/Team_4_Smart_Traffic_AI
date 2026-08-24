"""
app/routers/insights.py

FastAPI router for the AI Traffic Insights module.
"""
from uuid import UUID

from fastapi import APIRouter, Depends

from app.dependencies.auth import require_role
from app.dependencies.insight import get_insight_service
from app.models.user import UserRole
from app.schemas.insight import TrafficInsightRead
from app.services.insight_service import InsightService

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get(
    "/segment/{segment_id}",
    response_model=TrafficInsightRead,
    dependencies=[Depends(require_role(UserRole.TRAFFIC_CONTROLLER, UserRole.ADMIN))],
    summary="Get structured AI traffic insights for a segment",
)
async def get_segment_insight(
    segment_id: UUID,
    service: InsightService = Depends(get_insight_service),
) -> TrafficInsightRead:
    """
    Returns a deterministic structured traffic insight combining current traffic,
    historical trends, predictive models, active alerts, and routing intel.
    """
    return await service.generate_segment_insight(segment_id)
