"""
app/support/repositories/ticket_repository.py

Data-access layer for support tickets and related entities.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ticket import PRIORITY_SORT_WEIGHT, SupportTicket, TicketPriority, TicketStatus
from app.support.models.note import TicketNote
from app.support.models.reply import TicketReply
from app.timeline.models import TicketTimelineEvent


class TicketRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self,
        ticket_id: uuid.UUID,
        *,
        with_relations: bool = False,
    ) -> SupportTicket | None:
        query = select(SupportTicket).where(SupportTicket.id == ticket_id)
        if with_relations:
            query = query.options(
                selectinload(SupportTicket.notes).selectinload(TicketNote.author),
                selectinload(SupportTicket.replies).selectinload(TicketReply.author),
                selectinload(SupportTicket.timeline_events).selectinload(TicketTimelineEvent.actor),
                selectinload(SupportTicket.order),
                selectinload(SupportTicket.assigned_agent),
            )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_number(self, ticket_number: str) -> SupportTicket | None:
        result = await self.db.execute(
            select(SupportTicket).where(SupportTicket.ticket_number == ticket_number)
        )
        return result.scalar_one_or_none()

    async def count_all(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(SupportTicket))
        return int(result.scalar() or 0)

    async def next_ticket_number(self) -> str:
        now = datetime.now(timezone.utc)
        prefix = f"TK-{now.strftime('%Y%m%d')}-"
        result = await self.db.execute(
            select(func.count()).select_from(SupportTicket).where(
                SupportTicket.ticket_number.like(f"{prefix}%")
            )
        )
        count = int(result.scalar() or 0)
        return f"{prefix}{count + 1:03d}"

    def _priority_order(self):
        return case(
            {p.value: w for p, w in PRIORITY_SORT_WEIGHT.items()},
            value=SupportTicket.priority,
            else_=99,
        )

    async def list_tickets(
        self,
        *,
        customer_id: uuid.UUID | None = None,
        assigned_to: uuid.UUID | None = None,
        include_unassigned: bool = False,
        statuses: list[TicketStatus] | None = None,
        priorities: list[TicketPriority] | None = None,
        page: int = 1,
        per_page: int = 20,
        sort_queue: bool = True,
    ) -> tuple[list[SupportTicket], int]:
        filters = []
        if customer_id is not None:
            filters.append(SupportTicket.customer_id == customer_id)
        if assigned_to is not None and include_unassigned:
            filters.append(
                or_(
                    SupportTicket.assigned_to == assigned_to,
                    SupportTicket.assigned_to.is_(None),
                )
            )
        elif assigned_to is not None:
            filters.append(SupportTicket.assigned_to == assigned_to)
        if statuses:
            filters.append(SupportTicket.status.in_(statuses))
        if priorities:
            filters.append(SupportTicket.priority.in_(priorities))

        base = select(SupportTicket)
        if filters:
            base = base.where(and_(*filters))

        count_q = select(func.count()).select_from(base.subquery())
        total = int((await self.db.execute(count_q)).scalar() or 0)

        if sort_queue:
            # Priority → SLA → age (NULLS treated as last via coalescing)
            base = base.order_by(
                self._priority_order().asc(),
                SupportTicket.sla_deadline.asc(),
                SupportTicket.created_at.asc(),
            )
        else:
            base = base.order_by(SupportTicket.created_at.desc())

        offset = (page - 1) * per_page
        result = await self.db.execute(base.offset(offset).limit(per_page))
        return list(result.scalars().all()), total

    async def add(self, ticket: SupportTicket) -> SupportTicket:
        self.db.add(ticket)
        await self.db.flush()
        return ticket

    async def add_note(self, note: TicketNote) -> TicketNote:
        self.db.add(note)
        await self.db.flush()
        return note

    async def get_note(self, note_id: uuid.UUID) -> TicketNote | None:
        result = await self.db.execute(select(TicketNote).where(TicketNote.id == note_id))
        return result.scalar_one_or_none()

    async def add_reply(self, reply: TicketReply) -> TicketReply:
        self.db.add(reply)
        await self.db.flush()
        return reply

    async def list_timeline(self, ticket_id: uuid.UUID) -> list[TicketTimelineEvent]:
        result = await self.db.execute(
            select(TicketTimelineEvent)
            .where(TicketTimelineEvent.ticket_id == ticket_id)
            .order_by(TicketTimelineEvent.created_at.asc())
        )
        return list(result.scalars().all())
