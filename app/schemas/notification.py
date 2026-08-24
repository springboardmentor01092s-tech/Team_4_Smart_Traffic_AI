"""
app/schemas/notification.py

Pydantic v2 schemas for the Notification endpoints.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.notification import NotificationStatus


class NotificationCreate(BaseModel):
    recipient_user_id: uuid.UUID
    alert_id: uuid.UUID
    title: str = Field(min_length=5, max_length=200)
    message: str


class NotificationRead(BaseModel):
    id: uuid.UUID
    recipient_user_id: uuid.UUID
    alert_id: uuid.UUID
    
    title: str
    message: str
    
    status: NotificationStatus
    
    read_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }
