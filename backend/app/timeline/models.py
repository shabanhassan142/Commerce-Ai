"""
app/timeline/models.py

Every ticket action becomes a timeline event.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import JSON

from app.database.base import Base


class TimelineEventType(str, enum.Enum):
    TICKET_CREATED = "ticket_created"
    AI_ESCALATED = "ai_escalated"
    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"
    REASSIGNED = "reassigned"
    STATUS_CHANGED = "status_changed"
    PRIORITY_CHANGED = "priority_changed"
    CUSTOMER_REPLIED = "customer_replied"
    AGENT_REPLIED = "agent_replied"
    NOTE_ADDED = "note_added"
    NOTE_UPDATED = "note_updated"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"
    SLA_UPDATED = "sla_updated"


class TicketTimelineEvent(Base):
    """Immutable timeline entry for a support ticket."""

    __tablename__ = "ticket_timeline_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True,
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("support_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[TimelineEventType] = mapped_column(
        Enum(TimelineEventType, name="timelineeventtype", native_enum=False),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    event_data: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
    )

    ticket = relationship("SupportTicket", back_populates="timeline_events")
    actor = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return f"<TicketTimelineEvent type={self.event_type} ticket={self.ticket_id}>"
