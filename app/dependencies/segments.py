"""
app/dependencies/segments.py
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.camera_repository import CameraRepository
from app.repositories.segment_repository import SegmentRepository
from app.repositories.reading_repository import ReadingRepository
from app.services.segment_service import SegmentService


async def get_segment_service(db: AsyncSession = Depends(get_db)) -> SegmentService:
    return SegmentService(SegmentRepository(db), CameraRepository(db), ReadingRepository(db))
