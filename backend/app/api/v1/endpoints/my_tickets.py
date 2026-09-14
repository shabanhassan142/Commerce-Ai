"""
app/api/v1/endpoints/my_tickets.py

Customer portal ticket APIs — scoped to the authenticated customer only.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.auth.dependencies import require_role
from app.models.user import User, UserRole
from app.support.schemas import ReplyCreate
from app.support.services import TicketService
from app.utils.responses import success_response

router = APIRouter(prefix="/my/tickets", tags=["Customer Tickets"])


@router.get("", summary="List my tickets")
async def list_my_tickets(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.CUSTOMER)),
):
    data = await TicketService(db).list_for_user(
        user, page=page, per_page=per_page, status_filter=status_filter,
    )
    return success_response(data=data.model_dump(mode="json"))


@router.get("/{ticket_id}", summary="Get my ticket (no internal notes)")
async def get_my_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.CUSTOMER)),
):
    data = await TicketService(db).get_ticket(ticket_id, user)
    return success_response(data=data.model_dump(mode="json"))


@router.post("/{ticket_id}/reply", summary="Reply to my ticket", status_code=201)
async def reply_my_ticket(
    ticket_id: uuid.UUID,
    payload: ReplyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.CUSTOMER)),
):
    data = await TicketService(db).add_reply(ticket_id, user, payload, as_customer=True)
    return success_response(
        data=data.model_dump(mode="json"),
        message="Reply submitted",
        status_code=201,
    )
