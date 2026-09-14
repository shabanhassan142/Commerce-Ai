"""
app/support/models/note.py

Internal notes on support tickets — visible only to support/admin.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import JSON

from app.database.base import Base


class TicketNote(Base):
    """Internal agent note (customers cannot see these)."""

    __tablename__ = "ticket_notes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True,
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("support_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Edit history: [{content, edited_at, edited_by}, ...]
    edit_history: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=list,
    )

    ticket = relationship("SupportTicket", back_populates="notes")
    author = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return f"<TicketNote id={self.id} ticket={self.ticket_id}>"
