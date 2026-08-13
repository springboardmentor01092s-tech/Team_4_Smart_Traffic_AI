"""
app/dependencies/predictions.py

Dependency injection for the Predictions module.

Milestone 2 adds get_forecast_service which injects ReadingRepository
so that PredictionService.run_forecast() can access historical readings.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.reading_repository import ReadingRepository
from app.repositories.segment_repository import SegmentRepository
from app.services.prediction_service import PredictionService


def get_prediction_service(db: AsyncSession = Depends(get_db)) -> PredictionService:
    """Dependency provider for PredictionService (existing CRUD operations)."""
    return PredictionService(
        PredictionRepository(db),
        SegmentRepository(db),
    )


def get_forecast_service(db: AsyncSession = Depends(get_db)) -> PredictionService:
    """
    Dependency provider for PredictionService with ReadingRepository wired in.

    Used by the forecast endpoint (POST /predictions/segment/{id}/forecast)
    which requires access to historical readings for ML training.
    """
    return PredictionService(
        PredictionRepository(db),
        SegmentRepository(db),
        ReadingRepository(db),
    )
