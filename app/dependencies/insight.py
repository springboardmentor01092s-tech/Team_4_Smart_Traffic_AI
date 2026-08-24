"""
app/dependencies/insight.py

Dependency injection for the Insight module.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.alert_repository import AlertRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.reading_repository import ReadingRepository
from app.repositories.route_repository import RouteRepository
from app.repositories.segment_repository import SegmentRepository
from app.services.analytics_service import AnalyticsService
from app.services.route_service import RouteService
from app.services.insight_service import InsightService

def get_insight_service(db: AsyncSession = Depends(get_db)) -> InsightService:
    reading_repo = ReadingRepository(db)
    prediction_repo = PredictionRepository(db)
    alert_repo = AlertRepository(db)
    route_repo = RouteRepository(db)
    segment_repo = SegmentRepository(db)
    
    analytics_service = AnalyticsService(
        reading_repo=reading_repo,
        alert_repo=alert_repo,
        segment_repo=segment_repo,
        prediction_repo=prediction_repo
    )
    
    route_service = RouteService(
        route_repo=route_repo,
        segment_repo=segment_repo,
        reading_repo=reading_repo,
        prediction_repo=prediction_repo
    )

    return InsightService(
        reading_repo=reading_repo,
        prediction_repo=prediction_repo,
        alert_repo=alert_repo,
        route_repo=route_repo,
        analytics_service=analytics_service,
        route_service=route_service,
    )
