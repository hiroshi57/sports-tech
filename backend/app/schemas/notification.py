"""通知スキーマ(#19)。"""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.notification import NotificationType


class NotificationResponse(BaseModel):
    """通知レスポンス。"""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    type: NotificationType
    title: str
    body: str | None
    resource_id: uuid.UUID | None
    is_read: bool
    created_at: datetime


class UnreadCountResponse(BaseModel):
    """未読通知数レスポンス。"""

    unread_count: int
