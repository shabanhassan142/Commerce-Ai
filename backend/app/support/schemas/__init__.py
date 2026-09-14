"""
app/support/schemas/ticket.py

Pydantic schemas for Module 5 support ticket APIs.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class TicketCreate(BaseModel):
    subject: str = Field(..., min_length=3, max_length=300)
    description: str = Field(..., min_length=5, max_length=10000)
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    order_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None


class TicketUpdate(BaseModel):
    subject: str | None = Field(None, min_length=3, max_length=300)
    description: str | None = Field(None, min_length=5, max_length=10000)


class AssignTicketRequest(BaseModel):
    agent_id: uuid.UUID | None = Field(
        None,
        description="User ID of support agent. Null = unassign.",
    )


class StatusUpdateRequest(BaseModel):
    status: Literal[
        "open",
        "assigned",
        "in_progress",
        "waiting_for_customer",
        "waiting",
        "resolved",
        "closed",
        "reopened",
    ]


class PriorityUpdateRequest(BaseModel):
    priority: Literal["low", "medium", "high", "urgent"]


class NoteCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class NoteUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class ReplyCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    attachment_placeholder: str | None = Field(
        None, max_length=500, description="Placeholder for future file uploads",
    )


class NoteResponse(BaseModel):
    id: uuid.UUID
    ticket_id: uuid.UUID
    author_id: uuid.UUID | None
    author_name: str | None = None
    content: str
    edit_history: list[dict[str, Any]] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReplyResponse(BaseModel):
    id: uuid.UUID
    ticket_id: uuid.UUID
    author_id: uuid.UUID | None
    author_type: str
    author_name: str | None = None
    content: str
    attachment_placeholder: str | None = None
    is_ai_summary: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class TimelineEventResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    actor_id: uuid.UUID | None = None
    actor_label: str | None = None
    message: str
    metadata: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AISummaryResponse(BaseModel):
    issue_summary: str | None = None
    customer_intent: str | None = None
    relevant_orders: list[str] = []
    products_mentioned: list[str] = []
    suggested_resolution: str | None = None
    retrieved_knowledge: list[dict[str, Any]] = []
    confidence_score: float | None = None
    selected_agent: str | None = None
    escalation_reason: str | None = None


class TicketDetailResponse(BaseModel):
    id: uuid.UUID
    ticket_number: str
    subject: str
    description: str
    priority: str
    status: str
    customer_id: uuid.UUID
    customer_name: str | None = None
    customer_email: str | None = None
    customer_user_id: uuid.UUID | None = None
    customer_total_orders: int | None = None
    customer_total_spent: float | None = None
    order_id: uuid.UUID | None = None
    order_number: str | None = None
    order_status: str | None = None
    order_payment_status: str | None = None
    order_total_amount: float | None = None
    conversation_id: uuid.UUID | None = None
    assigned_to: uuid.UUID | None = None
    assigned_agent_name: str | None = None
    assigned_at: datetime | None = None
    last_updated_by: uuid.UUID | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    first_response_at: datetime | None = None
    resolution_time_seconds: int | None = None
    sla_deadline: datetime | None = None
    intent: str | None = None
    confidence: float | None = None
    suggested_department: str | None = None
    suggested_priority: str | None = None
    escalation_reason: str | None = None
    ai_summary: AISummaryResponse | None = None
    customer_satisfaction: int | None = None
    notes: list[NoteResponse] = []
    replies: list[ReplyResponse] = []
    timeline: list[TimelineEventResponse] = []
    created_at: datetime
    updated_at: datetime


class TicketListItem(BaseModel):
    id: uuid.UUID
    ticket_number: str
    subject: str
    priority: str
    status: str
    assigned_to: uuid.UUID | None = None
    sla_deadline: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None


class PaginatedTickets(BaseModel):
    items: list[TicketListItem]
    total: int
    page: int
    per_page: int
    pages: int


class DashboardStats(BaseModel):
    open_tickets: int
    assigned_tickets: int
    resolved_today: int
    urgent_tickets: int
    average_response_time_seconds: float | None
    average_resolution_time_seconds: float | None
    customer_satisfaction: float | None  # placeholder
    agent_workload: list[dict[str, Any]]
    escalations: int
    ai_resolution_percent: float | None
    human_resolution_percent: float | None
    total_tickets: int
    closed_tickets: int
    waiting_for_customer: int


class AdminWorkloadItem(BaseModel):
    agent_id: uuid.UUID
    agent_name: str
    agent_email: str
    open_assigned: int
    in_progress: int
    resolved_today: int
