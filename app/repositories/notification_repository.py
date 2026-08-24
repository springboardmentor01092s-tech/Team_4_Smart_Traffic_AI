"""
app/repositories/notification_repository.py

Data access layer for the Notification entity.
"""
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.notification import Notification, NotificationStatus

logger = get_logger(__name__)


class NotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, notification_id: uuid.UUID) -> Notification | None:
        result = await self._db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Notification]:
        query = (
            select(Notification)
            .where(
                Notification.recipient_user_id == user_id,
                Notification.deleted_at.is_(None)
            )
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self._db.execute(query)
        return result.scalars().all()
        
    async def get_by_alert_and_user(
        self, alert_id: uuid.UUID, user_id: uuid.UUID, for_update: bool = False
    ) -> Notification | None:
        query = select(Notification).where(
            Notification.alert_id == alert_id,
            Notification.recipient_user_id == user_id,
            Notification.deleted_at.is_(None)
        )
        if for_update and self._db.bind.dialect.name != "sqlite":
            query = query.with_for_update()
            
        result = await self._db.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        recipient_user_id: uuid.UUID,
        alert_id: uuid.UUID,
        title: str,
        message: str,
        status: NotificationStatus = NotificationStatus.PENDING,
    ) -> Notification:
        notification = Notification(
            recipient_user_id=recipient_user_id,
            alert_id=alert_id,
            title=title,
            message=message,
            status=status,
        )
        self._db.add(notification)
        await self._db.flush()
        await self._db.refresh(notification)
        logger.info("Notification created | id=%s recipient=%s", notification.id, recipient_user_id)
        return notification

    async def update(self, notification: Notification, **fields: object) -> Notification:
        for field, value in fields.items():
            setattr(notification, field, value)
        self._db.add(notification)
        await self._db.flush()
        await self._db.refresh(notification)
        logger.info("Notification updated | id=%s", notification.id)
        return notification

    async def soft_delete(self, notification: Notification) -> None:
        now = datetime.now(UTC)
        notification.deleted_at = now
        notification.updated_at = now
        self._db.add(notification)
        await self._db.flush()
        logger.warning("Notification soft-deleted | id=%s", notification.id)
