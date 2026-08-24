from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.reading_repository import ReadingRepository
from app.repositories.segment_repository import SegmentRepository
from app.services.reading_service import ReadingService

from app.dependencies.alerts import get_alert_service
from app.services.alert_service import AlertService
from app.services.alert_evaluator import AlertEvaluatorService
from app.dependencies.notifications import get_notification_service
from app.services.notification_service import NotificationService


def get_reading_service(
    db: AsyncSession = Depends(get_db),
    alert_service: AlertService = Depends(get_alert_service),
    notification_service: NotificationService = Depends(get_notification_service)
) -> ReadingService:
    evaluator = AlertEvaluatorService(alert_service, notification_service)
    return ReadingService(ReadingRepository(db), SegmentRepository(db), alert_evaluator=evaluator)
