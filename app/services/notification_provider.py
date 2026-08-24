"""
app/services/notification_provider.py

Abstractions for external notification delivery mechanisms.
"""
from abc import ABC, abstractmethod

from app.core.logging import get_logger
from app.models.notification import Notification

logger = get_logger(__name__)


class NotificationProvider(ABC):
    """Abstract base class for notification delivery providers."""
    
    @abstractmethod
    async def send(self, notification: Notification) -> bool:
        """
        Deliver the notification.
        Returns True if successful, False otherwise.
        """
        pass


class LogNotificationProvider(NotificationProvider):
    """A minimal provider that just logs the notification (useful for Stage 2)."""
    
    async def send(self, notification: Notification) -> bool:
        logger.info(
            "DELIVERING NOTIFICATION | User=%s | Alert=%s | Title=%r | Message=%r",
            notification.recipient_user_id,
            notification.alert_id,
            notification.title,
            notification.message,
        )
        # Always successful in this stub provider
        return True
