"""
app/support/services/ticket_service.py

Business logic for ticket lifecycle, assignment, notes, replies, and escalation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit
from app.core.logging import get_logger
from app.models.customer import Customer
from app.models.ticket import SupportTicket, TicketPriority, TicketStatus
from app.models.user import User, UserRole
from app.notifications.models import NotificationEventType
from app.notifications.service import enqueue_notification
from app.support.models.note import TicketNote
from app.support.models.reply import ReplyAuthorType, TicketReply
from app.support.repositories import TicketRepository
from app.support.schemas import (
    AISummaryResponse,
    AssignTicketRequest,
    DashboardStats,
    NoteCreate,
    NoteResponse,
    NoteUpdate,
    PaginatedTickets,
    PriorityUpdateRequest,
    ReplyCreate,
    ReplyResponse,
    StatusUpdateRequest,
    TicketCreate,
    TicketDetailResponse,
    TicketListItem,
    TicketUpdate,
    TimelineEventResponse,
)
from app.support.utils import (
    build_ai_summary,
    can_transition,
    compute_sla_deadline,
    enum_val,
    normalize_status,
    suggest_department,
    suggest_priority_from_context,
)
from app.timeline.models import TimelineEventType
from app.timeline.service import record_timeline_event

logger = get_logger(__name__)

OPEN_STATUSES = [
    TicketStatus.OPEN,
    TicketStatus.ASSIGNED,
    TicketStatus.IN_PROGRESS,
    TicketStatus.WAITING_FOR_CUSTOMER,
    TicketStatus.WAITING,
    TicketStatus.REOPENED,
]


class TicketService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TicketRepository(db)

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _get_customer(self, user: User) -> Customer:
        result = await self.db.execute(
            select(Customer).where(Customer.user_id == user.id)
        )
        customer = result.scalar_one_or_none()
        if not customer:
            customer = Customer(user_id=user.id)
            self.db.add(customer)
            await self.db.commit()
            await self.db.refresh(customer)
        return customer

    async def _ensure_access(self, ticket: SupportTicket, user: User) -> None:
        if user.role == UserRole.ADMIN:
            return
        if user.role == UserRole.SUPPORT:
            if ticket.assigned_to is None or ticket.assigned_to == user.id:
                return
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Support agents may only access assigned or unassigned tickets.",
            )
        customer = await self._get_customer(user)
        if ticket.customer_id != customer.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have access to this ticket.")

    def _to_list_item(self, t: SupportTicket) -> TicketListItem:
        return TicketListItem(
            id=t.id,
            ticket_number=t.ticket_number,
            subject=t.subject,
            priority=enum_val(t.priority),
            status=enum_val(normalize_status(t.status)),
            assigned_to=t.assigned_to,
            sla_deadline=t.sla_deadline,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )

    def _to_detail(
        self,
        t: SupportTicket,
        *,
        include_notes: bool = True,
    ) -> TicketDetailResponse:
        notes: list[NoteResponse] = []
        if include_notes:
            for n in (t.notes or []):
                notes.append(NoteResponse(
                    id=n.id,
                    ticket_id=n.ticket_id,
                    author_id=n.author_id,
                    author_name=n.author.full_name if n.author else None,
                    content=n.content,
                    edit_history=n.edit_history or [],
                    created_at=n.created_at,
                    updated_at=n.updated_at,
                ))

        replies = [
            ReplyResponse(
                id=r.id,
                ticket_id=r.ticket_id,
                author_id=r.author_id,
                author_type=enum_val(r.author_type),
                author_name=r.author.full_name if r.author else None,
                content=r.content,
                attachment_placeholder=r.attachment_placeholder,
                is_ai_summary=r.is_ai_summary,
                created_at=r.created_at,
            )
            for r in (t.replies or [])
        ]

        timeline = [
            TimelineEventResponse(
                id=e.id,
                event_type=enum_val(e.event_type),
                actor_id=e.actor_id,
                actor_label=e.actor_label,
                message=e.message,
                metadata=e.event_data,
                created_at=e.created_at,
            )
            for e in (t.timeline_events or [])
        ]

        ai_summary = None
        if t.ai_summary:
            ai_summary = AISummaryResponse(**{
                k: t.ai_summary.get(k)
                for k in AISummaryResponse.model_fields
            })

        c_name = t.customer.user.full_name if t.customer and t.customer.user else None
        c_email = t.customer.user.email if t.customer and t.customer.user else None
        c_user_id = t.customer.user.id if t.customer and t.customer.user else None

        o_status = enum_val(t.order.status) if t.order and t.order.status else None
        o_pay_status = enum_val(t.order.payment.status) if t.order and t.order.payment and hasattr(t.order.payment, "status") else None
        o_total = float(t.order.total_amount) if t.order and t.order.total_amount else None

        return TicketDetailResponse(
            id=t.id,
            ticket_number=t.ticket_number,
            subject=t.subject,
            description=t.description,
            priority=enum_val(t.priority),
            status=enum_val(normalize_status(t.status)),
            customer_id=t.customer_id,
            customer_name=c_name,
            customer_email=c_email,
            customer_user_id=c_user_id,
            order_id=t.order_id,
            order_number=t.order.order_number if t.order else None,
            order_status=o_status,
            order_payment_status=o_pay_status,
            order_total_amount=o_total,
            conversation_id=t.conversation_id,
            assigned_to=t.assigned_to,
            assigned_agent_name=t.assigned_agent.full_name if t.assigned_agent else None,
            assigned_at=t.assigned_at,
            last_updated_by=t.last_updated_by,
            resolved_at=t.resolved_at,
            closed_at=t.closed_at,
            first_response_at=t.first_response_at,
            resolution_time_seconds=t.resolution_time_seconds,
            sla_deadline=t.sla_deadline,
            intent=t.intent,
            confidence=t.confidence,
            suggested_department=t.suggested_department,
            suggested_priority=t.suggested_priority,
            escalation_reason=t.escalation_reason,
            ai_summary=ai_summary,
            customer_satisfaction=t.customer_satisfaction,
            notes=notes if include_notes else [],
            replies=replies,
            timeline=timeline,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )

    # ── CRUD / list ───────────────────────────────────────────────────────────

    async def list_for_user(
        self,
        user: User,
        *,
        page: int = 1,
        per_page: int = 20,
        status_filter: str | None = None,
        priority_filter: str | None = None,
        assigned_only: bool = False,
        open_only: bool = False,
        urgent_only: bool = False,
    ) -> PaginatedTickets:
        statuses = None
        priorities = None
        customer_id = None
        assigned_to = None
        include_unassigned = False

        if user.role == UserRole.CUSTOMER:
            customer = await self._get_customer(user)
            customer_id = customer.id
        elif user.role == UserRole.SUPPORT:
            assigned_to = user.id
            include_unassigned = not assigned_only
            if assigned_only:
                include_unassigned = False

        if status_filter:
            try:
                statuses = [TicketStatus(status_filter)]
            except ValueError:
                raise HTTPException(400, f"Invalid status: {status_filter}")
        if open_only:
            statuses = OPEN_STATUSES
        if priority_filter:
            try:
                priorities = [TicketPriority(priority_filter)]
            except ValueError:
                raise HTTPException(400, f"Invalid priority: {priority_filter}")
        if urgent_only:
            priorities = [TicketPriority.URGENT]

        tickets, total = await self.repo.list_tickets(
            customer_id=customer_id,
            assigned_to=assigned_to,
            include_unassigned=include_unassigned,
            statuses=statuses,
            priorities=priorities,
            page=page,
            per_page=per_page,
            sort_queue=user.role != UserRole.CUSTOMER,
        )
        pages = (total + per_page - 1) // per_page if per_page else 0
        return PaginatedTickets(
            items=[self._to_list_item(t) for t in tickets],
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
        )

    async def get_ticket(self, ticket_id: uuid.UUID, user: User) -> TicketDetailResponse:
        ticket = await self.repo.get_by_id(ticket_id, with_relations=True)
        if not ticket:
            raise HTTPException(404, "Ticket not found")
        await self._ensure_access(ticket, user)
        include_notes = user.role in (UserRole.SUPPORT, UserRole.ADMIN)
        return self._to_detail(ticket, include_notes=include_notes)

    async def create_ticket(self, user: User, payload: TicketCreate) -> TicketDetailResponse:
        if user.role == UserRole.CUSTOMER:
            customer = await self._get_customer(user)
        else:
            raise HTTPException(403, "Only customers can create tickets via this endpoint. Use escalation for AI.")

        priority = TicketPriority(payload.priority)
        ticket = SupportTicket(
            id=uuid.uuid4(),
            ticket_number=await self.repo.next_ticket_number(),
            customer_id=customer.id,
            order_id=payload.order_id,
            conversation_id=payload.conversation_id,
            subject=payload.subject,
            description=payload.description,
            priority=priority,
            status=TicketStatus.OPEN,
            last_updated_by=user.id,
            sla_deadline=compute_sla_deadline(priority),
        )
        await self.repo.add(ticket)
        await record_timeline_event(
            self.db,
            ticket_id=ticket.id,
            event_type=TimelineEventType.TICKET_CREATED,
            message=f"Ticket {ticket.ticket_number} created",
            actor_id=user.id,
            actor_label=user.full_name,
        )
        await record_audit(
            self.db,
            action="ticket.create",
            entity_type="support_ticket",
            entity_id=ticket.id,
            actor_id=user.id,
            new_value={"ticket_number": ticket.ticket_number, "priority": priority.value},
        )
        ticket = await self.repo.get_by_id(ticket.id, with_relations=True)
        return self._to_detail(ticket, include_notes=False)

    async def update_ticket(
        self, ticket_id: uuid.UUID, user: User, payload: TicketUpdate,
    ) -> TicketDetailResponse:
        if user.role == UserRole.CUSTOMER:
            raise HTTPException(403, "Customers cannot edit ticket metadata.")
        ticket = await self.repo.get_by_id(ticket_id, with_relations=True)
        if not ticket:
            raise HTTPException(404, "Ticket not found")
        await self._ensure_access(ticket, user)

        old = {"subject": ticket.subject, "description": ticket.description}
        if payload.subject is not None:
            ticket.subject = payload.subject
        if payload.description is not None:
            ticket.description = payload.description
        ticket.last_updated_by = user.id
        await self.db.flush()
        await record_audit(
            self.db,
            action="ticket.update",
            entity_type="support_ticket",
            entity_id=ticket.id,
            actor_id=user.id,
            old_value=old,
            new_value={"subject": ticket.subject, "description": ticket.description},
        )
        return self._to_detail(ticket, include_notes=True)

    # ── Assignment ────────────────────────────────────────────────────────────

    async def assign_ticket(
        self, ticket_id: uuid.UUID, user: User, payload: AssignTicketRequest,
    ) -> TicketDetailResponse:
        if user.role not in (UserRole.SUPPORT, UserRole.ADMIN):
            raise HTTPException(403, "Only support/admin can assign tickets.")

        ticket = await self.repo.get_by_id(ticket_id, with_relations=True)
        if not ticket:
            raise HTTPException(404, "Ticket not found")

        # Support can claim unassigned or reassign their own; admin can do anything
        if user.role == UserRole.SUPPORT:
            if ticket.assigned_to not in (None, user.id) and payload.agent_id != user.id:
                raise HTTPException(403, "Cannot reassign tickets owned by other agents.")

        agent_id = payload.agent_id
        if agent_id is not None:
            result = await self.db.execute(select(User).where(User.id == agent_id))
            agent = result.scalar_one_or_none()
            if not agent or agent.role not in (UserRole.SUPPORT, UserRole.ADMIN):
                raise HTTPException(400, "Assignee must be a support or admin user.")

        old_assigned = ticket.assigned_to
        now = datetime.now(timezone.utc)

        if agent_id is None:
            # Unassign
            ticket.assigned_to = None
            ticket.assigned_at = None
            if ticket.status == TicketStatus.ASSIGNED:
                ticket.status = TicketStatus.OPEN
            event = TimelineEventType.UNASSIGNED
            message = "Ticket unassigned"
            notif_recipient = old_assigned
        elif old_assigned and old_assigned != agent_id:
            ticket.assigned_to = agent_id
            ticket.assigned_at = now
            if ticket.status in (TicketStatus.OPEN, TicketStatus.REOPENED):
                ticket.status = TicketStatus.ASSIGNED
            event = TimelineEventType.REASSIGNED
            message = f"Ticket reassigned to agent {agent_id}"
            notif_recipient = agent_id
        else:
            ticket.assigned_to = agent_id
            ticket.assigned_at = now
            if ticket.status in (TicketStatus.OPEN, TicketStatus.REOPENED):
                ticket.status = TicketStatus.ASSIGNED
            event = TimelineEventType.ASSIGNED
            message = f"Ticket assigned to agent {agent_id}"
            notif_recipient = agent_id

        ticket.last_updated_by = user.id
        await self.db.flush()

        await record_timeline_event(
            self.db,
            ticket_id=ticket.id,
            event_type=event,
            message=message,
            actor_id=user.id,
            actor_label=user.full_name,
            metadata={"old": str(old_assigned) if old_assigned else None, "new": str(agent_id) if agent_id else None},
        )
        await record_audit(
            self.db,
            action="ticket.assign",
            entity_type="support_ticket",
            entity_id=ticket.id,
            actor_id=user.id,
            old_value={"assigned_to": str(old_assigned) if old_assigned else None},
            new_value={"assigned_to": str(agent_id) if agent_id else None},
        )
        if notif_recipient:
            await enqueue_notification(
                self.db,
                recipient_id=notif_recipient,
                event_type=NotificationEventType.TICKET_ASSIGNED,
                title=f"Ticket {ticket.ticket_number} assigned",
                body=message,
                payload={"ticket_id": str(ticket.id), "ticket_number": ticket.ticket_number},
            )

        ticket = await self.repo.get_by_id(ticket.id, with_relations=True)
        return self._to_detail(ticket)

    # ── Status / priority ─────────────────────────────────────────────────────

    async def update_status(
        self, ticket_id: uuid.UUID, user: User, payload: StatusUpdateRequest,
    ) -> TicketDetailResponse:
        if user.role == UserRole.CUSTOMER:
            # Customers may only reopen closed tickets
            if payload.status != "reopened":
                raise HTTPException(403, "Customers can only reopen closed tickets.")
        else:
            self._ensure_staff(user)

        ticket = await self.repo.get_by_id(ticket_id, with_relations=True)
        if not ticket:
            raise HTTPException(404, "Ticket not found")
        await self._ensure_access(ticket, user)

        try:
            new_status = TicketStatus(payload.status)
        except ValueError:
            raise HTTPException(400, f"Invalid status: {payload.status}")
        if new_status == TicketStatus.WAITING:
            new_status = TicketStatus.WAITING_FOR_CUSTOMER

        current = ticket.status
        if not can_transition(current, new_status):
            raise HTTPException(
                400,
                f"Invalid transition: {enum_val(current)} → {enum_val(new_status)}",
            )

        old = enum_val(current)
        ticket.status = new_status
        ticket.last_updated_by = user.id
        now = datetime.now(timezone.utc)

        event_type = TimelineEventType.STATUS_CHANGED
        if new_status == TicketStatus.RESOLVED:
            ticket.resolved_at = now
            if ticket.created_at:
                created_at = ticket.created_at if ticket.created_at.tzinfo else ticket.created_at.replace(tzinfo=timezone.utc)
                ticket.resolution_time_seconds = int((now - created_at).total_seconds())
            event_type = TimelineEventType.RESOLVED
        elif new_status == TicketStatus.CLOSED:
            ticket.closed_at = now
            if not ticket.resolved_at:
                ticket.resolved_at = now
            event_type = TimelineEventType.CLOSED
            # Notify customer
            await self._notify_customer(
                ticket,
                NotificationEventType.TICKET_CLOSED,
                f"Ticket {ticket.ticket_number} closed",
                "Your support ticket has been closed.",
            )
        elif new_status == TicketStatus.REOPENED:
            ticket.resolved_at = None
            ticket.closed_at = None
            ticket.resolution_time_seconds = None
            ticket.sla_deadline = compute_sla_deadline(ticket.priority, now)
            event_type = TimelineEventType.REOPENED

        await self.db.flush()
        await record_timeline_event(
            self.db,
            ticket_id=ticket.id,
            event_type=event_type,
            message=f"Status changed: {old} → {enum_val(new_status)}",
            actor_id=user.id,
            actor_label=user.full_name,
            metadata={"old": old, "new": enum_val(new_status)},
        )
        await record_audit(
            self.db,
            action="ticket.status_change",
            entity_type="support_ticket",
            entity_id=ticket.id,
            actor_id=user.id,
            old_value={"status": old},
            new_value={"status": enum_val(new_status)},
        )
        ticket = await self.repo.get_by_id(ticket.id, with_relations=True)
        return self._to_detail(ticket, include_notes=user.role != UserRole.CUSTOMER)

    async def update_priority(
        self, ticket_id: uuid.UUID, user: User, payload: PriorityUpdateRequest,
    ) -> TicketDetailResponse:
        if user.role not in (UserRole.SUPPORT, UserRole.ADMIN):
            raise HTTPException(403, "Only support/admin can change priority.")
        ticket = await self.repo.get_by_id(ticket_id, with_relations=True)
        if not ticket:
            raise HTTPException(404, "Ticket not found")
        await self._ensure_access(ticket, user)

        old = enum_val(ticket.priority)
        new_priority = TicketPriority(payload.priority)
        ticket.priority = new_priority
        ticket.sla_deadline = compute_sla_deadline(new_priority)
        ticket.last_updated_by = user.id
        await self.db.flush()

        await record_timeline_event(
            self.db,
            ticket_id=ticket.id,
            event_type=TimelineEventType.PRIORITY_CHANGED,
            message=f"Priority changed: {old} → {new_priority.value}",
            actor_id=user.id,
            actor_label=user.full_name,
            metadata={"old": old, "new": new_priority.value},
        )
        await record_audit(
            self.db,
            action="ticket.priority_change",
            entity_type="support_ticket",
            entity_id=ticket.id,
            actor_id=user.id,
            old_value={"priority": old},
            new_value={"priority": new_priority.value},
        )
        ticket = await self.repo.get_by_id(ticket.id, with_relations=True)
        return self._to_detail(ticket)

    def _ensure_staff(self, user: User) -> None:
        if user.role not in (UserRole.SUPPORT, UserRole.ADMIN):
            raise HTTPException(403, "Staff access required.")

    # ── Notes / replies ───────────────────────────────────────────────────────

    async def add_note(
        self, ticket_id: uuid.UUID, user: User, payload: NoteCreate,
    ) -> NoteResponse:
        if user.role not in (UserRole.SUPPORT, UserRole.ADMIN):
            raise HTTPException(403, "Only support/admin can add internal notes.")
        ticket = await self.repo.get_by_id(ticket_id)
        if not ticket:
            raise HTTPException(404, "Ticket not found")
        await self._ensure_access(ticket, user)

        note = TicketNote(
            id=uuid.uuid4(),
            ticket_id=ticket.id,
            author_id=user.id,
            content=payload.content,
            edit_history=[],
        )
        await self.repo.add_note(note)
        ticket.last_updated_by = user.id
        await record_timeline_event(
            self.db,
            ticket_id=ticket.id,
            event_type=TimelineEventType.NOTE_ADDED,
            message="Internal note added",
            actor_id=user.id,
            actor_label=user.full_name,
        )
        await record_audit(
            self.db,
            action="ticket.note_add",
            entity_type="ticket_note",
            entity_id=note.id,
            actor_id=user.id,
            new_value={"ticket_id": str(ticket.id)},
        )
        return NoteResponse(
            id=note.id,
            ticket_id=note.ticket_id,
            author_id=note.author_id,
            author_name=user.full_name,
            content=note.content,
            edit_history=[],
            created_at=note.created_at,
            updated_at=note.updated_at,
        )

    async def update_note(
        self, ticket_id: uuid.UUID, note_id: uuid.UUID, user: User, payload: NoteUpdate,
    ) -> NoteResponse:
        if user.role not in (UserRole.SUPPORT, UserRole.ADMIN):
            raise HTTPException(403, "Only support/admin can edit notes.")
        note = await self.repo.get_note(note_id)
        if not note or note.ticket_id != ticket_id:
            raise HTTPException(404, "Note not found")
        ticket = await self.repo.get_by_id(ticket_id)
        await self._ensure_access(ticket, user)

        history = list(note.edit_history or [])
        history.append({
            "content": note.content,
            "edited_at": datetime.now(timezone.utc).isoformat(),
            "edited_by": str(user.id),
        })
        note.edit_history = history
        note.content = payload.content
        await self.db.flush()
        await record_timeline_event(
            self.db,
            ticket_id=ticket_id,
            event_type=TimelineEventType.NOTE_UPDATED,
            message="Internal note updated",
            actor_id=user.id,
            actor_label=user.full_name,
        )
        return NoteResponse(
            id=note.id,
            ticket_id=note.ticket_id,
            author_id=note.author_id,
            author_name=user.full_name,
            content=note.content,
            edit_history=note.edit_history,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )

    async def add_reply(
        self,
        ticket_id: uuid.UUID,
        user: User,
        payload: ReplyCreate,
        *,
        as_customer: bool = False,
    ) -> ReplyResponse:
        ticket = await self.repo.get_by_id(ticket_id, with_relations=True)
        if not ticket:
            raise HTTPException(404, "Ticket not found")
        await self._ensure_access(ticket, user)

        is_customer = as_customer or user.role == UserRole.CUSTOMER
        author_type = ReplyAuthorType.CUSTOMER if is_customer else ReplyAuthorType.SUPPORT
        reply = TicketReply(
            id=uuid.uuid4(),
            ticket_id=ticket.id,
            author_id=user.id,
            author_type=author_type,
            content=payload.content,
            attachment_placeholder=payload.attachment_placeholder,
            is_ai_summary=False,
        )
        await self.repo.add_reply(reply)
        now = datetime.now(timezone.utc)
        ticket.last_updated_by = user.id

        if is_customer:
            if ticket.status in (
                TicketStatus.WAITING_FOR_CUSTOMER,
                TicketStatus.WAITING,
                TicketStatus.RESOLVED,
            ):
                ticket.status = TicketStatus.IN_PROGRESS
            event = TimelineEventType.CUSTOMER_REPLIED
            # Notify assigned agent
            if ticket.assigned_to:
                await enqueue_notification(
                    self.db,
                    recipient_id=ticket.assigned_to,
                    event_type=NotificationEventType.CUSTOMER_REPLY,
                    title=f"Customer replied on {ticket.ticket_number}",
                    body=payload.content[:200],
                    payload={"ticket_id": str(ticket.id)},
                )
        else:
            if ticket.first_response_at is None:
                ticket.first_response_at = now
            if ticket.status in (TicketStatus.OPEN, TicketStatus.ASSIGNED, TicketStatus.REOPENED):
                ticket.status = TicketStatus.IN_PROGRESS
            event = TimelineEventType.AGENT_REPLIED

        await self.db.flush()
        await record_timeline_event(
            self.db,
            ticket_id=ticket.id,
            event_type=event,
            message="Customer replied" if is_customer else "Agent replied",
            actor_id=user.id,
            actor_label=user.full_name,
        )
        await record_audit(
            self.db,
            action="ticket.reply",
            entity_type="ticket_reply",
            entity_id=reply.id,
            actor_id=user.id,
            new_value={"author_type": author_type.value, "ticket_id": str(ticket.id)},
        )
        return ReplyResponse(
            id=reply.id,
            ticket_id=reply.ticket_id,
            author_id=reply.author_id,
            author_type=author_type.value,
            author_name=user.full_name,
            content=reply.content,
            attachment_placeholder=reply.attachment_placeholder,
            is_ai_summary=False,
            created_at=reply.created_at,
        )

    async def _notify_customer(
        self,
        ticket: SupportTicket,
        event_type: NotificationEventType,
        title: str,
        body: str,
    ) -> None:
        result = await self.db.execute(
            select(Customer).where(Customer.id == ticket.customer_id)
        )
        customer = result.scalar_one_or_none()
        if customer:
            await enqueue_notification(
                self.db,
                recipient_id=customer.user_id,
                event_type=event_type,
                title=title,
                body=body,
                payload={"ticket_id": str(ticket.id), "ticket_number": ticket.ticket_number},
            )

    # ── AI Escalation (Module 4 integration) ──────────────────────────────────

    async def create_from_escalation(
        self,
        *,
        user_id: str,
        subject: str,
        description: str,
        priority: str = "medium",
        order_number: str | None = None,
        conversation_id: str | None = None,
        intent: str | None = None,
        confidence: float | None = None,
        escalation_reason: str | None = None,
        selected_agent: str | None = None,
        order_context: dict[str, Any] | None = None,
        tool_results: list[dict[str, Any]] | None = None,
        retrieved_documents: list[dict[str, Any]] | None = None,
        customer_message: str = "",
    ) -> dict[str, Any]:
        """Create an enriched ticket from LangGraph escalation. Used by ticket_tools."""
        from app.models.order import Order

        cust_result = await self.db.execute(
            select(Customer).where(Customer.user_id == uuid.UUID(user_id))
        )
        customer = cust_result.scalar_one_or_none()
        if not customer:
            return {"error": "Customer profile not found"}

        order_id = None
        if order_number:
            order_result = await self.db.execute(
                select(Order).where(
                    Order.order_number == order_number.upper(),
                    Order.customer_id == customer.id,
                )
            )
            order = order_result.scalar_one_or_none()
            if order:
                order_id = order.id

        ticket_priority = suggest_priority_from_context(intent, confidence, priority)
        ai_summary = build_ai_summary(
            customer_message=customer_message or description,
            intent=intent,
            confidence=confidence,
            order_context=order_context,
            tool_results=tool_results,
            retrieved_documents=retrieved_documents,
            escalation_reason=escalation_reason,
            selected_agent=selected_agent,
        )

        conv_uuid = None
        if conversation_id:
            try:
                conv_uuid = uuid.UUID(conversation_id)
            except ValueError:
                conv_uuid = None

        ticket = SupportTicket(
            id=uuid.uuid4(),
            ticket_number=await self.repo.next_ticket_number(),
            customer_id=customer.id,
            order_id=order_id,
            conversation_id=conv_uuid,
            subject=subject[:300],
            description=description,
            priority=ticket_priority,
            status=TicketStatus.OPEN,
            sla_deadline=compute_sla_deadline(ticket_priority),
            intent=intent,
            confidence=confidence,
            suggested_department=suggest_department(intent),
            suggested_priority=ticket_priority.value,
            escalation_reason=escalation_reason,
            ai_summary=ai_summary,
            retrieved_documents=retrieved_documents,
        )
        await self.repo.add(ticket)

        await record_timeline_event(
            self.db,
            ticket_id=ticket.id,
            event_type=TimelineEventType.TICKET_CREATED,
            message=f"Ticket {ticket.ticket_number} created",
            actor_label="system",
        )
        await record_timeline_event(
            self.db,
            ticket_id=ticket.id,
            event_type=TimelineEventType.AI_ESCALATED,
            message=escalation_reason or "Escalated from AI agent",
            actor_label="ai_supervisor",
            metadata={
                "intent": intent,
                "confidence": confidence,
                "department": ticket.suggested_department,
            },
        )
        await record_audit(
            self.db,
            action="ticket.ai_escalation",
            entity_type="support_ticket",
            entity_id=ticket.id,
            new_value={
                "ticket_number": ticket.ticket_number,
                "intent": intent,
                "confidence": confidence,
            },
            description="Created via LangGraph escalation",
        )

        # Notify all support users about escalation
        support_result = await self.db.execute(
            select(User).where(User.role == UserRole.SUPPORT, User.is_active.is_(True))
        )
        for agent in support_result.scalars().all():
            await enqueue_notification(
                self.db,
                recipient_id=agent.id,
                event_type=NotificationEventType.ESCALATION_CREATED,
                title=f"New escalation {ticket.ticket_number}",
                body=subject,
                payload={
                    "ticket_id": str(ticket.id),
                    "priority": ticket_priority.value,
                    "intent": intent,
                },
            )

        await self.db.commit()

        return {
            "ticket_number": ticket.ticket_number,
            "ticket_id": str(ticket.id),
            "subject": subject,
            "priority": ticket_priority.value,
            "status": "open",
            "suggested_department": ticket.suggested_department,
            "ai_summary": ai_summary,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        }

    # ── Dashboard / admin stats ───────────────────────────────────────────────

    async def dashboard_stats(self, user: User) -> DashboardStats:
        if user.role not in (UserRole.SUPPORT, UserRole.ADMIN):
            raise HTTPException(403, "Staff access required.")

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        async def _count(*filters) -> int:
            q = select(func.count()).select_from(SupportTicket)
            if filters:
                q = q.where(and_(*filters))
            return int((await self.db.execute(q)).scalar() or 0)

        total = await _count()
        open_tickets = await _count(SupportTicket.status.in_(OPEN_STATUSES))
        assigned = await _count(
            SupportTicket.assigned_to.is_not(None),
            SupportTicket.status.in_(OPEN_STATUSES),
        )
        resolved_today = await _count(
            SupportTicket.resolved_at >= today_start,
        )
        urgent = await _count(
            SupportTicket.priority == TicketPriority.URGENT,
            SupportTicket.status.in_(OPEN_STATUSES),
        )
        closed = await _count(SupportTicket.status == TicketStatus.CLOSED)
        waiting = await _count(
            SupportTicket.status.in_([TicketStatus.WAITING_FOR_CUSTOMER, TicketStatus.WAITING])
        )
        escalations = await _count(SupportTicket.confidence.is_not(None))

        # Avg response / resolution (computed in Python for SQLite + Postgres portability)
        resp_rows = await self.db.execute(
            select(SupportTicket.created_at, SupportTicket.first_response_at).where(
                SupportTicket.first_response_at.is_not(None)
            )
        )
        deltas = []
        for created, first in resp_rows.all():
            if created and first:
                deltas.append((first - created).total_seconds())
        avg_response = sum(deltas) / len(deltas) if deltas else None

        res_time = await self.db.execute(
            select(func.avg(SupportTicket.resolution_time_seconds)).where(
                SupportTicket.resolution_time_seconds.is_not(None)
            )
        )
        avg_resolution = res_time.scalar()

        # Agent workload
        workload_q = await self.db.execute(
            select(
                User.id,
                User.full_name,
                func.count(SupportTicket.id),
            )
            .outerjoin(
                SupportTicket,
                and_(
                    SupportTicket.assigned_to == User.id,
                    SupportTicket.status.in_(OPEN_STATUSES),
                ),
            )
            .where(User.role.in_([UserRole.SUPPORT, UserRole.ADMIN]), User.is_active.is_(True))
            .group_by(User.id, User.full_name)
        )
        agent_workload = [
            {"agent_id": str(row[0]), "agent_name": row[1], "open_assigned": row[2]}
            for row in workload_q.all()
        ]

        human_resolved = await _count(
            SupportTicket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
            SupportTicket.assigned_to.is_not(None),
        )
        # AI resolution approx: conversations without tickets — placeholder ratio
        ai_res_pct = None
        human_res_pct = None
        if total > 0:
            human_res_pct = round((human_resolved / total) * 100, 1)
            ai_res_pct = round(max(0.0, 100.0 - human_res_pct), 1)

        return DashboardStats(
            open_tickets=open_tickets,
            assigned_tickets=assigned,
            resolved_today=resolved_today,
            urgent_tickets=urgent,
            average_response_time_seconds=float(avg_response) if avg_response else None,
            average_resolution_time_seconds=float(avg_resolution) if avg_resolution else None,
            customer_satisfaction=None,  # placeholder
            agent_workload=agent_workload,
            escalations=escalations,
            ai_resolution_percent=ai_res_pct,
            human_resolution_percent=human_res_pct,
            total_tickets=total,
            closed_tickets=closed,
            waiting_for_customer=waiting,
        )
