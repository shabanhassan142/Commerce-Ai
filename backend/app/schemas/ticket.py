"""
app/schemas/ticket.py

Pydantic schemas for SupportTicket-related API responses.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class TicketResponse(BaseModel):
    """Full ticket detail in API responses."""
    id: uuid.UUID
    ticket_number: str
    subject: str
    description: str
    priority: str
    status: str
    order_id: uuid.UUID | None = None
    order_number: str | None = None
    assigned_to: uuid.UUID | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_order(cls, ticket) -> "TicketResponse":
        """Build response including order number."""
        return cls(
            id=ticket.id,
            ticket_number=ticket.ticket_number,
            subject=ticket.subject,
            description=ticket.description,
            priority=ticket.priority.value if hasattr(ticket.priority, "value") else ticket.priority,
            status=ticket.status.value if hasattr(ticket.status, "value") else ticket.status,
            order_id=ticket.order_id,
            order_number=ticket.order.order_number if ticket.order else None,
            assigned_to=ticket.assigned_to,
            resolved_at=ticket.resolved_at,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
        )


class TicketListItem(BaseModel):
    """Compact ticket for list views."""
    id: uuid.UUID
    ticket_number: str
    subject: str
    priority: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
