from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.reading_repository import ReadingRepository
from app.repositories.segment_repository import SegmentRepository
from app.services.reading_service import ReadingService


def get_reading_service(db: AsyncSession = Depends(get_db)) -> ReadingService:
    return ReadingService(ReadingRepository(db), SegmentRepository(db))
