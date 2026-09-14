"""
app/models/ticket.py

Support ticket model.
Customers can create tickets linked to orders for support issues.
Module 5 extends lifecycle, assignment, SLA, and AI escalation metadata.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import JSON

from app.database.base import Base


class TicketPriority(str, enum.Enum):
    """Ticket priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketStatus(str, enum.Enum):
    """
    Ticket lifecycle statuses (Module 5).

    OPEN → ASSIGNED → IN_PROGRESS → WAITING_FOR_CUSTOMER → RESOLVED → CLOSED
    CLOSED → REOPENED
    """
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_CUSTOMER = "waiting_for_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"
    # Backward-compat alias used by Module 2 seed data
    WAITING = "waiting"


# Priority → SLA hours from creation / last reopen
SLA_HOURS: dict[TicketPriority, int] = {
    TicketPriority.URGENT: 4,
    TicketPriority.HIGH: 8,
    TicketPriority.MEDIUM: 24,
    TicketPriority.LOW: 48,
}

PRIORITY_SORT_WEIGHT: dict[TicketPriority, int] = {
    TicketPriority.URGENT: 0,
    TicketPriority.HIGH: 1,
    TicketPriority.MEDIUM: 2,
    TicketPriority.LOW: 3,
}

VALID_STATUS_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.OPEN: {TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS, TicketStatus.CLOSED},
    TicketStatus.ASSIGNED: {
        TicketStatus.IN_PROGRESS,
        TicketStatus.OPEN,
        TicketStatus.WAITING_FOR_CUSTOMER,
        TicketStatus.CLOSED,
    },
    TicketStatus.IN_PROGRESS: {
        TicketStatus.WAITING_FOR_CUSTOMER,
        TicketStatus.RESOLVED,
        TicketStatus.ASSIGNED,
        TicketStatus.CLOSED,
    },
    TicketStatus.WAITING_FOR_CUSTOMER: {
        TicketStatus.IN_PROGRESS,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED,
    },
    TicketStatus.WAITING: {
        TicketStatus.IN_PROGRESS,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED,
        TicketStatus.WAITING_FOR_CUSTOMER,
    },
    TicketStatus.RESOLVED: {TicketStatus.CLOSED, TicketStatus.REOPENED},
    TicketStatus.CLOSED: {TicketStatus.REOPENED},
    TicketStatus.REOPENED: {
        TicketStatus.ASSIGNED,
        TicketStatus.IN_PROGRESS,
        TicketStatus.CLOSED,
    },
}


class SupportTicket(Base):
    """Customer support ticket with full Module 5 lifecycle support."""

    __tablename__ = "support_tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    ticket_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True,
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    order_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, name="ticketpriority", native_enum=False),
        nullable=False,
        default=TicketPriority.MEDIUM,
    )

    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticketstatus", native_enum=False),
        nullable=False,
        default=TicketStatus.OPEN,
    )

    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    last_updated_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    first_response_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # Resolution time in seconds (created/reopened → resolved)
    resolution_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    sla_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True,
    )

    # AI escalation metadata (Module 4 → 5)
    intent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    suggested_department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    suggested_priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    escalation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Structured AI summary for human agents
    ai_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    retrieved_documents: Mapped[list | None] = mapped_column(JSON, nullable=True)

    customer_satisfaction: Mapped[int | None] = mapped_column(Integer, nullable=True)  # placeholder 1-5

    # ── Relationships ─────────────────────────────────────────────────────────
    customer = relationship("Customer", back_populates="tickets", lazy="selectin")
    order = relationship("Order", back_populates="tickets", lazy="selectin")
    assigned_agent = relationship(
        "User", foreign_keys=[assigned_to], lazy="selectin",
    )
    last_updater = relationship(
        "User", foreign_keys=[last_updated_by], lazy="selectin",
    )
    conversation = relationship("Conversation", lazy="selectin")
    notes = relationship(
        "TicketNote", back_populates="ticket", lazy="noload",
        order_by="TicketNote.created_at",
    )
    replies = relationship(
        "TicketReply", back_populates="ticket", lazy="noload",
        order_by="TicketReply.created_at",
    )
    timeline_events = relationship(
        "TicketTimelineEvent", back_populates="ticket", lazy="noload",
        order_by="TicketTimelineEvent.created_at",
    )

    def __repr__(self) -> str:
        return f"<SupportTicket {self.ticket_number} status={self.status}>"
