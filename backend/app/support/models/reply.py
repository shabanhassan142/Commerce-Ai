"""
app/support/models/reply.py

Customer and agent replies on support tickets.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ReplyAuthorType(str, enum.Enum):
    CUSTOMER = "customer"
    SUPPORT = "support"
    SYSTEM = "system"


class TicketReply(Base):
    """Public reply on a ticket (visible to customer and agents)."""

    __tablename__ = "ticket_replies"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True,
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("support_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    author_type: Mapped[ReplyAuthorType] = mapped_column(
        Enum(ReplyAuthorType, name="replyauthortype", native_enum=False),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Placeholder for future file uploads
    attachment_placeholder: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_ai_summary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    ticket = relationship("SupportTicket", back_populates="replies")
    author = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return f"<TicketReply id={self.id} type={self.author_type}>"
