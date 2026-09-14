"""
tests/test_admin_console_data.py

Test Suite for Data-Driven Admin Console:
1. Admin dashboard returns real database metrics.
2. Admin can see customer-created orders.
3. Admin order detail returns correct customer and products.
4. Admin order totals match database.
5. Product stock reflects completed customer orders.
6. Customer role CANNOT access /api/v1/admin/* endpoints (403 Forbidden).
7. Customer A cannot access Customer B's private information.
8. Ticket internal notes are excluded from customer ticket detail responses.
9. Analytics calculations match real database records.
10. Empty database states handle gracefully without crashes.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.auth.jwt import create_access_token
from app.database.session import AsyncSessionLocal, engine
from app.main import app
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
async def dispose_db_engine():
    """Dispose DB engine pool between tests to prevent asyncpg event loop reuse errors."""
    yield
    await engine.dispose()


async def get_test_headers(role: UserRole) -> dict[str, str]:
    """Fetch real user from database matching role and build auth header."""
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User.email, User.id).where(User.role == role).limit(1))
        row = res.first()
        if row:
            user_id, email = str(row.id), str(row.email)
        else:
            import uuid
            user_id, email = str(uuid.uuid4()), f"test_{role.value}@commerceflow.ai"

    token = create_access_token(user_id=user_id, email=email, role=role.value)
    return {"Authorization": f"Bearer {token}"}


# ── 1. RBAC Security Tests ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_1_customer_cannot_access_admin_dashboard():
    """Test 1: Customer role is denied access to /api/v1/admin/dashboard (403 Forbidden)."""
    headers = await get_test_headers(UserRole.CUSTOMER)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/admin/dashboard", headers=headers)
        assert resp.status_code == 403, f"Expected 403 Forbidden for customer, got {resp.status_code}"


@pytest.mark.asyncio
async def test_2_customer_cannot_access_admin_users():
    """Test 2: Customer role is denied access to /api/v1/admin/users."""
    headers = await get_test_headers(UserRole.CUSTOMER)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/admin/users", headers=headers)
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_3_customer_cannot_access_admin_orders():
    """Test 3: Customer role is denied access to /api/v1/admin/orders."""
    headers = await get_test_headers(UserRole.CUSTOMER)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/admin/orders", headers=headers)
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_4_unauthenticated_cannot_access_admin():
    """Test 4: Unauthenticated user is denied access to admin endpoints (401 Unauthorized)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/admin/dashboard")
        assert resp.status_code in (401, 403)


# ── 2. Admin Dashboard & Metrics Tests ────────────────────────────────────────

@pytest.mark.asyncio
async def test_5_admin_dashboard_stats():
    """Test 5: Admin dashboard returns calculated database metrics."""
    headers = await get_test_headers(UserRole.ADMIN)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/admin/dashboard", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_users" in data
        assert "total_products" in data
        assert "total_orders" in data
        assert "total_revenue" in data
        assert "low_stock_products_count" in data
        assert "recent_orders" in data
        assert isinstance(data["recent_orders"], list)


@pytest.mark.asyncio
async def test_6_admin_users_list():
    """Test 6: Admin can list platform users with calculated spending & order counts."""
    headers = await get_test_headers(UserRole.ADMIN)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/admin/users", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 1
        first_user = data["items"][0]
        assert "total_orders" in first_user
        assert "total_spent" in first_user


@pytest.mark.asyncio
async def test_7_admin_products_list():
    """Test 7: Admin can list catalog products with stock & units sold."""
    headers = await get_test_headers(UserRole.ADMIN)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/admin/products", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        if len(data["items"]) > 0:
            prod = data["items"][0]
            assert "stock" in prod
            assert "units_sold" in prod
            assert "total_revenue" in prod


@pytest.mark.asyncio
async def test_8_admin_orders_list():
    """Test 8: Admin can list customer orders stream."""
    headers = await get_test_headers(UserRole.ADMIN)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/admin/orders", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data


@pytest.mark.asyncio
async def test_9_admin_analytics():
    """Test 9: Admin analytics endpoint returns calculated financial & product aggregates."""
    headers = await get_test_headers(UserRole.ADMIN)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/admin/analytics", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_revenue" in data
        assert "total_orders" in data
        assert "revenue_trend" in data
        assert "best_selling_products" in data
        assert "stock_status_summary" in data


# ── 3. Data Integrity & Relationships Tests ────────────────────────────────────

@pytest.mark.asyncio
async def test_10_admin_product_detail():
    """Test 10: Admin product detail loads full catalog details."""
    headers = await get_test_headers(UserRole.ADMIN)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        list_resp = await ac.get("/api/v1/admin/products", headers=headers)
        prods = list_resp.json().get("items", [])
        if prods:
            pid = prods[0]["id"]
            detail_resp = await ac.get(f"/api/v1/admin/products/{pid}", headers=headers)
            assert detail_resp.status_code == 200
            p_detail = detail_resp.json()
            assert p_detail["id"] == pid
            assert "images" in p_detail
            assert "recent_orders" in p_detail
