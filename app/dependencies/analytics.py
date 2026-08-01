"""
app/dependencies/analytics.py

Dependency injection for the Analytics module.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.alert_repository import AlertRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.reading_repository import ReadingRepository
from app.repositories.segment_repository import SegmentRepository
from app.services.analytics_service import AnalyticsService


def get_analytics_service(db: AsyncSession = Depends(get_db)) -> AnalyticsService:
    """Provides an instance of AnalyticsService with its repositories."""
    return AnalyticsService(
        reading_repo=ReadingRepository(db),
        alert_repo=AlertRepository(db),
        segment_repo=SegmentRepository(db),
        prediction_repo=PredictionRepository(db),
    )
