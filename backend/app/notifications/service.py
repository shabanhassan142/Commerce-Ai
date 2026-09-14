"""
app/notifications/service.py

Notification infrastructure — queue events only; no sending yet.
Future channels: Email, SMS, Push, WebSocket.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationEventType,
)

logger = get_logger(__name__)


async def enqueue_notification(
    db: AsyncSession,
    *,
    recipient_id: uuid.UUID,
    event_type: NotificationEventType,
    title: str,
    body: str,
    payload: dict[str, Any] | None = None,
    channel: NotificationChannel = NotificationChannel.IN_APP,
) -> Notification:
    """
    Persist a notification for later delivery.
    Does NOT send email/SMS/push/websocket yet.
    """
    notification = Notification(
        id=uuid.uuid4(),
        recipient_id=recipient_id,
        event_type=event_type,
        channel=channel,
        title=title,
        body=body,
        payload=payload or {},
        is_read=False,
        is_sent=False,
    )
    db.add(notification)
    await db.flush()
    logger.info(
        f"Notification queued: event={event_type.value} recipient={recipient_id} "
        f"(sending deferred)"
    )
    return notification
