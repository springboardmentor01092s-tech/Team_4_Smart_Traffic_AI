"""
app/services/notification_service.py

Business logic for the Notification domain.
"""
import uuid

from app.core.logging import get_logger
from app.models.alert import Alert
from app.models.notification import NotificationStatus, Notification
from app.models.user import UserRole
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repository import UserRepository
from app.services.notification_provider import NotificationProvider

logger = get_logger(__name__)


class NotificationService:
    def __init__(
        self,
        notification_repo: NotificationRepository,
        user_repo: UserRepository,
        provider: NotificationProvider,
    ) -> None:
        self._notification_repo = notification_repo
        self._user_repo = user_repo
        self._provider = provider

    async def generate_notifications_for_alert(self, alert: Alert) -> list[Notification]:
        """
        Generates notifications for an alert to appropriate recipients.
        Ensures deduplication (alert + recipient).
        """
        # Fetch appropriate ADMIN / TRAFFIC_CONTROLLER users
        recipients = await self._user_repo.get_by_roles([UserRole.ADMIN, UserRole.TRAFFIC_CONTROLLER])
        
        notifications_created = []
        for user in recipients:
            # Idempotency check: don't create duplicate notifications for the same alert+user
            existing = await self._notification_repo.get_by_alert_and_user(
                alert_id=alert.id, user_id=user.id, for_update=True
            )
            if existing is not None:
                continue

            notification = await self._notification_repo.create(
                recipient_user_id=user.id,
                alert_id=alert.id,
                title=f"New Alert: {alert.title}",
                message=alert.description or "No description provided.",
            )
            
            # Send notification
            success = await self._provider.send(notification)
            
            # Update status
            new_status = NotificationStatus.SENT if success else NotificationStatus.FAILED
            notification = await self._notification_repo.update(notification, status=new_status)
            
            notifications_created.append(notification)
            
        logger.info("Generated %d notifications for alert_id=%s", len(notifications_created), alert.id)
        return notifications_created
