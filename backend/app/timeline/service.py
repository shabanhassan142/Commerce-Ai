"""
app/timeline/service.py

Record timeline events for ticket actions.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.timeline.models import TicketTimelineEvent, TimelineEventType


async def record_timeline_event(
    db: AsyncSession,
    *,
    ticket_id: uuid.UUID,
    event_type: TimelineEventType,
    message: str,
    actor_id: uuid.UUID | None = None,
    actor_label: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> TicketTimelineEvent:
    event = TicketTimelineEvent(
        id=uuid.uuid4(),
        ticket_id=ticket_id,
        event_type=event_type,
        actor_id=actor_id,
        actor_label=actor_label or ("system" if actor_id is None else None),
        message=message,
        event_data=metadata,
    )
    db.add(event)
    await db.flush()
    return event
