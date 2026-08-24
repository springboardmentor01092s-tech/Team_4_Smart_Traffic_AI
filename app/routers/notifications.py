"""
app/routers/notifications.py

FastAPI router for Notification endpoints.
"""
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_user
from app.dependencies.notifications import get_notification_repo
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import NotificationRead

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "/me",
    response_model=list[NotificationRead],
    summary="Get my notifications",
)
async def get_my_notifications(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    notification_repo: NotificationRepository = Depends(get_notification_repo),
) -> list[NotificationRead]:
    """
    Retrieve all notifications belonging to the currently authenticated user.
    """
    return list(await notification_repo.get_by_user(user_id=current_user.id, skip=skip, limit=limit))


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationRead,
    summary="Mark notification as read",
)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    notification_repo: NotificationRepository = Depends(get_notification_repo),
) -> NotificationRead:
    """
    Mark a specific notification as read.
    """
    notification = await notification_repo.get_by_id(notification_id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
        
    if notification.recipient_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this notification",
        )

    if not notification.read_at:
        notification = await notification_repo.update(notification, read_at=datetime.now(UTC))
        
    return notification
