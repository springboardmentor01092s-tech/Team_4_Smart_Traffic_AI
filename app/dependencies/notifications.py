"""
app/dependencies/notifications.py

Dependencies for the Notification domain.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repository import UserRepository
from app.services.notification_provider import LogNotificationProvider, NotificationProvider
from app.services.notification_service import NotificationService


def get_notification_repo(db: AsyncSession = Depends(get_db)) -> NotificationRepository:
    return NotificationRepository(db)


def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_notification_provider() -> NotificationProvider:
    # We can inject a real provider later, but for now use the Log stub
    return LogNotificationProvider()


def get_notification_service(
    notification_repo: NotificationRepository = Depends(get_notification_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    provider: NotificationProvider = Depends(get_notification_provider),
) -> NotificationService:
    return NotificationService(notification_repo, user_repo, provider)
