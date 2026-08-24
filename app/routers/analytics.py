"""
app/routers/analytics.py

FastAPI router for the Analytics module.

Milestone 2 addition:
  GET /analytics/predictions  — prediction performance report.
"""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies.auth import require_role
from app.dependencies.analytics import get_analytics_service
from app.models.user import UserRole
from app.models.prediction import PredictionStatus
from app.schemas.analytics import (
    AnalyticsSummaryRead,
    FullReportRead,
    HeatmapItemRead,
    HistoryBucketRead,
    PeakHourRead,
    PredictionReportRead,
    SegmentTrendsRead,
    AITrafficReportRead
)
from app.services.analytics_service import AnalyticsService
from app.services.insight_service import InsightService
from app.dependencies.insight import get_insight_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary", response_model=AnalyticsSummaryRead)
async def get_summary(
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsSummaryRead:
    """System-wide snapshot."""
    return await service.get_summary()


@router.get("/congestion-heatmap", response_model=list[HeatmapItemRead])
async def get_congestion_heatmap(
    service: AnalyticsService = Depends(get_analytics_service),
) -> list[HeatmapItemRead]:
    """All segments with latest congestion level."""
    return await service.get_congestion_heatmap()


@router.get("/peak-hours", response_model=list[PeakHourRead])
async def get_peak_hours(
    from_dt: datetime | None = Query(None),
    to_dt: datetime | None = Query(None),
    service: AnalyticsService = Depends(get_analytics_service),
) -> list[PeakHourRead]:
    """Hourly vehicle count averages."""
    return await service.get_peak_hour_averages(from_dt, to_dt)


@router.get("/segments/{segment_id}/history", response_model=list[HistoryBucketRead])
async def get_segment_history(
    segment_id: UUID,
    bucket_minutes: int = Query(60),
    from_dt: datetime | None = Query(None),
    to_dt: datetime | None = Query(None),
    service: AnalyticsService = Depends(get_analytics_service),
) -> list[HistoryBucketRead]:
    """Historical readings (date range, aggregated)."""
    return await service.get_segment_history(segment_id, from_dt, to_dt, bucket_minutes)


@router.get(
    "/segments/{segment_id}/trends",
    response_model=SegmentTrendsRead,
    dependencies=[Depends(require_role(UserRole.TRAFFIC_CONTROLLER, UserRole.ADMIN))],
)
async def get_segment_trends(
    segment_id: UUID,
    service: AnalyticsService = Depends(get_analytics_service),
) -> SegmentTrendsRead:
    """Statistical trends."""
    return await service.get_segment_trends(segment_id)


@router.get(
    "/predictions",
    response_model=PredictionReportRead,
    dependencies=[Depends(require_role(UserRole.TRAFFIC_CONTROLLER, UserRole.ADMIN))],
    summary="Prediction performance report",
)
async def get_prediction_report(
    segment_id: UUID | None = Query(None, description="Filter by segment UUID"),
    status: PredictionStatus | None = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: AnalyticsService = Depends(get_analytics_service),
) -> PredictionReportRead:
    """
    Prediction performance report.

    Returns counts and per-prediction detail for forecasts made via the
    ML-powered forecast endpoint. Supports filtering by segment and status.
    TRAFFIC_CONTROLLER and ADMIN only.
    """
    return await service.get_prediction_report(
        segment_id=segment_id,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/reports",
    response_model=FullReportRead,
    dependencies=[Depends(require_role(UserRole.TRAFFIC_CONTROLLER, UserRole.ADMIN))],
)
async def get_full_report(
    from_dt: datetime = Query(...),
    to_dt: datetime = Query(...),
    service: AnalyticsService = Depends(get_analytics_service),
) -> FullReportRead:
    return await service.get_full_report(from_dt, to_dt)

@router.get(
    "/ai-report",
    response_model=AITrafficReportRead,
    dependencies=[Depends(require_role(UserRole.TRAFFIC_CONTROLLER, UserRole.ADMIN))],
    summary="Generate system-level AI traffic report",
)
async def get_ai_report(
    from_dt: datetime | None = Query(None, description="Start date/time"),
    to_dt: datetime | None = Query(None, description="End date/time"),
    service: AnalyticsService = Depends(get_analytics_service),
    insight_service: InsightService = Depends(get_insight_service),
) -> AITrafficReportRead:
    """
    Generate a comprehensive AI traffic report over a specified date range.
    Defaults to the last 24 hours if no date range is provided.
    Bounded insights are derived deterministically for the most critical segments.
    """
    return await service.get_ai_report(
        insight_service=insight_service,
        from_dt=from_dt,
        to_dt=to_dt,
    )
