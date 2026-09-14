"""
app/audit/service.py

Persist audit logs for support platform mutations.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditLog


async def record_audit(
    db: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: str | uuid.UUID,
    actor_id: uuid.UUID | None = None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    description: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        id=uuid.uuid4(),
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        old_values=old_value,
        new_values=new_value,
        description=description,
    )
    db.add(entry)
    await db.flush()
    return entry
