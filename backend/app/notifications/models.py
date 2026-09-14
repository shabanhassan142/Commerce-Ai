"""
app/notifications/models.py

Notification queue — backend only; sending deferred (email/SMS/push/WS).
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import JSON

from app.database.base import Base


class NotificationEventType(str, enum.Enum):
    TICKET_ASSIGNED = "ticket_assigned"
    CUSTOMER_REPLY = "customer_reply"
    TICKET_CLOSED = "ticket_closed"
    ESCALATION_CREATED = "escalation_created"
    TICKET_REOPENED = "ticket_reopened"
    PRIORITY_CHANGED = "priority_changed"
    STATUS_CHANGED = "status_changed"


class NotificationChannel(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBSOCKET = "websocket"


class Notification(Base):
    """Queued notification record (not sent yet)."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True,
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[NotificationEventType] = mapped_column(
        Enum(NotificationEventType, name="notificationeventtype", native_enum=False),
        nullable=False,
        index=True,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notificationchannel", native_enum=False),
        nullable=False,
        default=NotificationChannel.IN_APP,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    recipient = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Notification event={self.event_type} recipient={self.recipient_id}>"
