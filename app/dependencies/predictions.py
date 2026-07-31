from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.segment_repository import SegmentRepository
from app.services.prediction_service import PredictionService


def get_prediction_service(db: AsyncSession = Depends(get_db)) -> PredictionService:
    """Dependency provider for PredictionService."""
    return PredictionService(
        PredictionRepository(db),
        SegmentRepository(db),
    )
