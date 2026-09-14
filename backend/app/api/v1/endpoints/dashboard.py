"""
app/api/v1/endpoints/dashboard.py

Support / Admin dashboard statistics for the React console.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.auth.dependencies import require_role
from app.models.user import User, UserRole
from app.support.services import TicketService
from app.utils.responses import success_response

router = APIRouter(prefix="/dashboard", tags=["Support Dashboard"])


@router.get("/stats", summary="Support operations dashboard statistics")
async def dashboard_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.SUPPORT, UserRole.ADMIN)),
):
    data = await TicketService(db).dashboard_stats(user)
    return success_response(data=data.model_dump(mode="json"), message="Dashboard stats")


@router.get("/admin/stats", summary="Admin overview (same stats, admin-gated)")
async def admin_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    data = await TicketService(db).dashboard_stats(user)
    return success_response(data=data.model_dump(mode="json"), message="Admin dashboard stats")
