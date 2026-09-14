"""
app/api/v1/endpoints/tickets.py

Module 5 — Support queue APIs for human agents and shared ticket operations.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.auth.dependencies import get_current_active_user, require_role
from app.models.user import User, UserRole
from app.support.schemas import (
    AssignTicketRequest,
    NoteCreate,
    NoteUpdate,
    PriorityUpdateRequest,
    ReplyCreate,
    StatusUpdateRequest,
    TicketCreate,
    TicketUpdate,
)
from app.support.services import TicketService
from app.utils.responses import error_response, success_response

router = APIRouter(prefix="/tickets", tags=["Support Tickets"])


def _svc(db: AsyncSession) -> TicketService:
    return TicketService(db)


# ── Static path routes FIRST (before /{ticket_id}) ────────────────────────────

@router.get("/assigned/me", summary="Tickets assigned to current support agent")
async def tickets_assigned_to_me(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.SUPPORT, UserRole.ADMIN)),
):
    data = await _svc(db).list_for_user(
        user, page=page, per_page=per_page, assigned_only=True,
    )
    return success_response(data=data.model_dump(mode="json"), message="Assigned tickets")


@router.get("/open", summary="Open ticket queue")
async def open_tickets(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.SUPPORT, UserRole.ADMIN)),
):
    data = await _svc(db).list_for_user(
        user, page=page, per_page=per_page, open_only=True,
    )
    return success_response(data=data.model_dump(mode="json"), message="Open tickets")


@router.get("/urgent", summary="Urgent ticket queue")
async def urgent_tickets(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.SUPPORT, UserRole.ADMIN)),
):
    data = await _svc(db).list_for_user(
        user, page=page, per_page=per_page, urgent_only=True, open_only=True,
    )
    return success_response(data=data.model_dump(mode="json"), message="Urgent tickets")


@router.get("", summary="List support tickets")
async def list_tickets(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    priority_filter: str | None = Query(None, alias="priority"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    data = await _svc(db).list_for_user(
        user,
        page=page,
        per_page=per_page,
        status_filter=status_filter,
        priority_filter=priority_filter,
    )
    return success_response(data=data.model_dump(mode="json"))


@router.post("", summary="Create a support ticket (customer)", status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.CUSTOMER)),
):
    data = await _svc(db).create_ticket(user, payload)
    return success_response(
        data=data.model_dump(mode="json"),
        message="Ticket created",
        status_code=201,
    )


@router.get("/{ticket_id}", summary="Get ticket details")
async def get_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    data = await _svc(db).get_ticket(ticket_id, user)
    return success_response(data=data.model_dump(mode="json"))


@router.patch("/{ticket_id}", summary="Update ticket subject/description")
async def patch_ticket(
    ticket_id: uuid.UUID,
    payload: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.SUPPORT, UserRole.ADMIN)),
):
    data = await _svc(db).update_ticket(ticket_id, user, payload)
    return success_response(data=data.model_dump(mode="json"), message="Ticket updated")


@router.patch("/{ticket_id}/assign", summary="Assign, reassign, or unassign ticket")
async def assign_ticket(
    ticket_id: uuid.UUID,
    payload: AssignTicketRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.SUPPORT, UserRole.ADMIN)),
):
    data = await _svc(db).assign_ticket(ticket_id, user, payload)
    return success_response(data=data.model_dump(mode="json"), message="Assignment updated")


@router.patch("/{ticket_id}/status", summary="Update ticket status")
async def update_status(
    ticket_id: uuid.UUID,
    payload: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    try:
        data = await _svc(db).update_status(ticket_id, user, payload)
        return success_response(data=data.model_dump(mode="json"), message="Status updated")
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return error_response(str(e), 400)


@router.patch("/{ticket_id}/priority", summary="Update ticket priority")
async def update_priority(
    ticket_id: uuid.UUID,
    payload: PriorityUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.SUPPORT, UserRole.ADMIN)),
):
    data = await _svc(db).update_priority(ticket_id, user, payload)
    return success_response(data=data.model_dump(mode="json"), message="Priority updated")


@router.post("/{ticket_id}/notes", summary="Add internal note", status_code=201)
async def add_note(
    ticket_id: uuid.UUID,
    payload: NoteCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.SUPPORT, UserRole.ADMIN)),
):
    data = await _svc(db).add_note(ticket_id, user, payload)
    return success_response(data=data.model_dump(mode="json"), message="Note added", status_code=201)


@router.patch("/{ticket_id}/notes/{note_id}", summary="Edit internal note (tracks history)")
async def edit_note(
    ticket_id: uuid.UUID,
    note_id: uuid.UUID,
    payload: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.SUPPORT, UserRole.ADMIN)),
):
    data = await _svc(db).update_note(ticket_id, note_id, user, payload)
    return success_response(data=data.model_dump(mode="json"), message="Note updated")


@router.post("/{ticket_id}/reply", summary="Agent or customer reply on ticket", status_code=201)
async def reply_to_ticket(
    ticket_id: uuid.UUID,
    payload: ReplyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    data = await _svc(db).add_reply(ticket_id, user, payload)
    return success_response(data=data.model_dump(mode="json"), message="Reply added", status_code=201)
