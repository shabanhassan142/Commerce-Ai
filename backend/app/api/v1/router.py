"""
app/api/v1/router.py

Aggregates all v1 API routers.
Add new routers here as modules are implemented.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.products import router as products_router
from app.api.v1.endpoints.orders import router as orders_router
from app.api.v1.endpoints.tickets import router as tickets_router
from app.api.v1.endpoints.my_tickets import router as my_tickets_router
from app.api.v1.endpoints.dashboard import router as dashboard_router
from app.api.v1.endpoints.knowledge import router as knowledge_router
from app.api.v1.endpoints.chat import router as chat_router
from app.api.v1.endpoints.admin import router as admin_router

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(health_router)
v1_router.include_router(auth_router)
v1_router.include_router(products_router)
v1_router.include_router(orders_router)
v1_router.include_router(tickets_router)
v1_router.include_router(my_tickets_router)
v1_router.include_router(dashboard_router)
v1_router.include_router(knowledge_router)
v1_router.include_router(chat_router)
v1_router.include_router(admin_router)


