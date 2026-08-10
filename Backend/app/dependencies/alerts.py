"""
app/dependencies/alerts.py
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.alert_repository import AlertRepository
from app.repositories.segment_repository import SegmentRepository
from app.services.alert_service import AlertService


async def get_alert_service(db: AsyncSession = Depends(get_db)) -> AlertService:
    return AlertService(AlertRepository(db), SegmentRepository(db))
