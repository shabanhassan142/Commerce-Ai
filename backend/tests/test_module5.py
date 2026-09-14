"""
tests/test_module5.py

Unit + integration tests for Module 5 — Support Operations Platform.

Fixture design (matches test_auth.py pattern):
  - test_engine: session-scoped SQLite in-memory engine with StaticPool
    StaticPool ensures all connections share the SAME in-memory database.
    Without StaticPool each new connection gets a blank SQLite DB, causing
    "another operation is in progress" errors from the asyncpg dialect shim.
  - db_session: function-scoped — drops/recreates schema each test for isolation.
  - client: injects the test session as the FastAPI DB dependency.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database.base import Base
import app.models  # noqa: F401
from app.auth.password import hash_password
from app.database.session import get_db as session_get_db
from app.api.deps import get_db
from app.main import app
from app.models.customer import Customer
from app.models.ticket import SupportTicket, TicketPriority, TicketStatus
from app.models.user import User, UserRole
from app.support.utils import can_transition, compute_sla_deadline
from app.agents.utils.product_query import normalize_product_query


# ── Unit: status / query normalization ────────────────────────────────────────

def test_valid_status_transitions():
    assert can_transition(TicketStatus.OPEN, TicketStatus.ASSIGNED)
    assert can_transition(TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS)
    assert can_transition(TicketStatus.IN_PROGRESS, TicketStatus.WAITING_FOR_CUSTOMER)
    assert can_transition(TicketStatus.WAITING_FOR_CUSTOMER, TicketStatus.RESOLVED)
    assert can_transition(TicketStatus.RESOLVED, TicketStatus.CLOSED)
    assert can_transition(TicketStatus.CLOSED, TicketStatus.REOPENED)
    assert can_transition(TicketStatus.OPEN, TicketStatus.CLOSED)  # cancel path
    assert not can_transition(TicketStatus.CLOSED, TicketStatus.IN_PROGRESS)


def test_product_query_normalization():
    q = normalize_product_query("Find wireless bluetooth earbuds")
    assert "find" not in q.split()
    assert "earbuds" in q
    assert "wireless" in q
    assert "earbuds" in normalize_product_query("earphones under 3000")


def test_sla_deadline_urgent_sooner_than_low():
    from datetime import datetime, timezone
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    urgent = compute_sla_deadline(TicketPriority.URGENT, base)
    low = compute_sla_deadline(TicketPriority.LOW, base)
    assert urgent < low


# ── Integration fixtures ──────────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
async def test_engine():
    """
    Session-scoped SQLite in-memory engine.

    StaticPool is critical: it forces all connections to reuse the SAME
    underlying SQLite connection, so the schema and data created during
    setup are visible to every subsequent query in the same test process.
    Without StaticPool, each new connection opens a fresh empty database.
    connect_args check_same_thread=False allows cross-thread access (safe
    here because we use asyncio, not threads).
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    """
    Function-scoped session: drops and recreates all tables before each test
    to provide full isolation without leaving leftover data.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    async with Session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session):
    """
    Async HTTP client with DB dependency overridden to use the test session.
    Overrides both get_db aliases (app.api.deps and app.database.session).
    """
    async def override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[session_get_db] = override_get_db
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


async def _create_user(db: AsyncSession, *, email: str, role: UserRole, name: str) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        full_name=name,
        hashed_password=hash_password("TestPass123!"),
        role=role,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    return user


async def _create_customer(db: AsyncSession, user: User) -> Customer:
    cust = Customer(id=uuid.uuid4(), user_id=user.id, loyalty_points=0)
    db.add(cust)
    await db.flush()
    return cust


async def _login(client: AsyncClient, email: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "TestPass123!"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    token = body["data"]["tokens"]["access_token"]
    assert token
    return token


@pytest.fixture
async def seeded(db_session):
    customer_user = await _create_user(
        db_session, email="cust@test.com", role=UserRole.CUSTOMER, name="Cust"
    )
    support_user = await _create_user(
        db_session, email="sup@test.com", role=UserRole.SUPPORT, name="Sup"
    )
    admin_user = await _create_user(
        db_session, email="adm@test.com", role=UserRole.ADMIN, name="Adm"
    )
    other_support = await _create_user(
        db_session, email="sup2@test.com", role=UserRole.SUPPORT, name="Sup2"
    )
    customer = await _create_customer(db_session, customer_user)
    await db_session.commit()
    return {
        "customer_user": customer_user,
        "support_user": support_user,
        "admin_user": admin_user,
        "other_support": other_support,
        "customer": customer,
    }


# ── API tests ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_customer_create_and_list_tickets(client, seeded):
    token = await _login(client, "cust@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    create = await client.post(
        "/api/v1/tickets",
        headers=headers,
        json={
            "subject": "Late delivery",
            "description": "My order has not arrived yet after 10 days.",
            "priority": "high",
        },
    )
    assert create.status_code == 201, create.text
    ticket = create.json()["data"]
    assert ticket["status"] == "open"
    assert ticket["ticket_number"].startswith("TK-")
    assert ticket["sla_deadline"] is not None

    mine = await client.get("/api/v1/my/tickets", headers=headers)
    assert mine.status_code == 200
    assert mine.json()["data"]["total"] >= 1


@pytest.mark.asyncio
async def test_assignment_notes_reply_status_priority(client, seeded):
    cust_token = await _login(client, "cust@test.com")
    sup_token = await _login(client, "sup@test.com")
    cust_h = {"Authorization": f"Bearer {cust_token}"}
    sup_h = {"Authorization": f"Bearer {sup_token}"}

    created = await client.post(
        "/api/v1/tickets",
        headers=cust_h,
        json={"subject": "Refund help", "description": "Need refund for damaged item please."},
    )
    ticket_id = created.json()["data"]["id"]
    support_id = str(seeded["support_user"].id)

    # Assign
    assigned = await client.patch(
        f"/api/v1/tickets/{ticket_id}/assign",
        headers=sup_h,
        json={"agent_id": support_id},
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["data"]["status"] == "assigned"
    assert assigned.json()["data"]["assigned_to"] == support_id

    # Priority
    pri = await client.patch(
        f"/api/v1/tickets/{ticket_id}/priority",
        headers=sup_h,
        json={"priority": "urgent"},
    )
    assert pri.status_code == 200
    assert pri.json()["data"]["priority"] == "urgent"

    # Status → in_progress
    st = await client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        headers=sup_h,
        json={"status": "in_progress"},
    )
    assert st.status_code == 200, st.text
    assert st.json()["data"]["status"] == "in_progress"

    # Internal note
    note = await client.post(
        f"/api/v1/tickets/{ticket_id}/notes",
        headers=sup_h,
        json={"content": "Customer very frustrated. Refund already approved."},
    )
    assert note.status_code == 201

    # Customer must NOT see notes
    detail_cust = await client.get(f"/api/v1/my/tickets/{ticket_id}", headers=cust_h)
    assert detail_cust.status_code == 200
    assert detail_cust.json()["data"]["notes"] == []

    # Support sees notes
    detail_sup = await client.get(f"/api/v1/tickets/{ticket_id}", headers=sup_h)
    assert len(detail_sup.json()["data"]["notes"]) >= 1
    assert len(detail_sup.json()["data"]["timeline"]) >= 1

    # Customer reply
    reply = await client.post(
        f"/api/v1/my/tickets/{ticket_id}/reply",
        headers=cust_h,
        json={"content": "Thanks, please process ASAP.", "attachment_placeholder": "photo.jpg"},
    )
    assert reply.status_code == 201

    # Resolve → close
    res = await client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        headers=sup_h,
        json={"status": "resolved"},
    )
    assert res.status_code == 200, res.text
    closed = await client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        headers=sup_h,
        json={"status": "closed"},
    )
    assert closed.status_code == 200
    assert closed.json()["data"]["status"] == "closed"


@pytest.mark.asyncio
async def test_rbac_customer_cannot_access_others(client, db_session, seeded):
    other_user = await _create_user(
        db_session, email="other@test.com", role=UserRole.CUSTOMER, name="Other"
    )
    other_cust = await _create_customer(db_session, other_user)
    ticket = SupportTicket(
        id=uuid.uuid4(),
        ticket_number="TK-TEST-001",
        customer_id=other_cust.id,
        subject="Secret",
        description="Should not be visible",
        priority=TicketPriority.LOW,
        status=TicketStatus.OPEN,
    )
    db_session.add(ticket)
    await db_session.commit()

    token = await _login(client, "cust@test.com")
    resp = await client.get(
        f"/api/v1/my/tickets/{ticket.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (403, 404) or (
        resp.status_code == 200 and resp.json().get("success") is False
    ) or resp.status_code == 403


@pytest.mark.asyncio
async def test_dashboard_stats_admin(client, seeded):
    token = await _login(client, "adm@test.com")
    resp = await client.get(
        "/api/v1/dashboard/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert "open_tickets" in data
    assert "urgent_tickets" in data
    assert "agent_workload" in data


@pytest.mark.asyncio
async def test_invalid_status_transition(client, seeded):
    cust_token = await _login(client, "cust@test.com")
    sup_token = await _login(client, "sup@test.com")
    created = await client.post(
        "/api/v1/tickets",
        headers={"Authorization": f"Bearer {cust_token}"},
        json={"subject": "Transition test", "description": "Testing invalid jump to resolved"},
    )
    ticket_id = created.json()["data"]["id"]
    # OPEN → RESOLVED should fail
    bad = await client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        headers={"Authorization": f"Bearer {sup_token}"},
        json={"status": "resolved"},
    )
    assert bad.status_code in (400, 422) or bad.json().get("success") is False


@pytest.mark.asyncio
async def test_queues_assigned_open_urgent(client, seeded):
    token = await _login(client, "sup@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    for path in ("/api/v1/tickets/assigned/me", "/api/v1/tickets/open", "/api/v1/tickets/urgent"):
        resp = await client.get(path, headers=headers)
        assert resp.status_code == 200, f"{path}: {resp.text}"


# ── Product catalog tests (no DB fixture needed — uses live DB) ────────────────

@pytest.mark.asyncio
async def test_product_catalog_quality():
    """Products API returns real product data (not seeds or placeholders)."""
    async with AsyncClient(base_url="http://127.0.0.1:8000") as ac:
        resp = await ac.get("/api/v1/products?per_page=30")
    assert resp.status_code == 200
    res_json = resp.json()
    data = res_json.get("data", res_json)
    assert data["total"] == 30
    items = data["items"]
    # Every product must have a real brand
    for item in items:
        assert item.get("brand"), f"Missing brand: {item['name']}"
    # Prices should be realistic (no $749 USB cable)
    prices = [float(item["price"]) for item in items]
    assert max(prices) < 5000, f"Unrealistic max price: {max(prices)}"
    assert min(prices) > 5, f"Unrealistic min price: {min(prices)}"


@pytest.mark.asyncio
async def test_product_api_with_gallery():
    """Each product should have at least 2 images in its gallery."""
    async with AsyncClient(base_url="http://127.0.0.1:8000") as ac:
        list_resp = await ac.get("/api/v1/products?per_page=5")
    assert list_resp.status_code == 200
    res_json = list_resp.json()
    items = res_json.get("data", res_json)["items"]
    for item in items:
        assert len(item["images"]) >= 2, (
            f"Product '{item['name']}' has only {len(item['images'])} image(s)"
        )


@pytest.mark.asyncio
async def test_end_to_end_support_lifecycle_and_internal_notes_security(client, seeded):
    """
    Complete end-to-end verification:
    1. Customer creates ticket.
    2. Support Agent claims ticket and posts a public reply AND a private internal note 🔒.
    3. Customer reads ticket detail — verifies support reply is visible but internal note is 100% EXCLUDED.
    4. Customer sends a reply.
    5. Support Agent sees customer reply and updates status to RESOLVED.
    6. Customer sees ticket status as RESOLVED.
    """
    cust_token = await _login(client, "cust@test.com")
    sup_token = await _login(client, "sup@test.com")
    cust_headers = {"Authorization": f"Bearer {cust_token}"}
    sup_headers = {"Authorization": f"Bearer {sup_token}"}

    # 1. Customer creates ticket
    create_res = await client.post(
        "/api/v1/tickets",
        headers=cust_headers,
        json={
            "subject": "[Delivery] Package not arrived",
            "description": "My package with tracking #CF-101 is delayed. Please check status.",
            "priority": "high",
        },
    )
    assert create_res.status_code == 201
    ticket_id = create_res.json()["data"]["id"]

    # 2. Support Agent assigns to self
    assign_res = await client.patch(
        f"/api/v1/tickets/{ticket_id}/assign",
        headers=sup_headers,
        json={"agent_id": str(seeded["support_user"].id)},
    )
    assert assign_res.status_code == 200

    # 2b. Agent adds internal note (PRIVATE 🔒)
    note_res = await client.post(
        f"/api/v1/tickets/{ticket_id}/notes",
        headers=sup_headers,
        json={"content": "Check carrier API log. Potential courier delay in Lahore warehouse."},
    )
    assert note_res.status_code == 201

    # 2c. Agent sends public reply to customer
    reply_res = await client.post(
        f"/api/v1/tickets/{ticket_id}/reply",
        headers=sup_headers,
        json={"content": "Hello! I am investigating your delivery status with our warehouse team."},
    )
    assert reply_res.status_code == 201

    # 3. SECURITY VERIFICATION: Customer reads ticket
    cust_read = await client.get(f"/api/v1/tickets/{ticket_id}", headers=cust_headers)
    assert cust_read.status_code == 200
    cust_detail = cust_read.json()["data"]

    # Support agent reply MUST be present
    assert len(cust_detail["replies"]) == 1
    assert "investigating your delivery status" in cust_detail["replies"][0]["content"]

    # Internal notes MUST be empty / hidden for customer
    assert cust_detail.get("notes") == [], "CRITICAL SECURITY RISK: Internal notes exposed to customer!"

    # 4. Customer replies
    cust_reply_res = await client.post(
        f"/api/v1/tickets/{ticket_id}/reply",
        headers=cust_headers,
        json={"content": "Thank you for the quick update!"},
    )
    assert cust_reply_res.status_code == 201

    # 5. Agent marks ticket as IN_PROGRESS then RESOLVED
    await client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        headers=sup_headers,
        json={"status": "in_progress"},
    )

    resolve_res = await client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        headers=sup_headers,
        json={"status": "resolved"},
    )
    assert resolve_res.status_code == 200

    # 6. Customer reads ticket — status is resolved
    final_cust_read = await client.get(f"/api/v1/tickets/{ticket_id}", headers=cust_headers)
    assert final_cust_read.status_code == 200
    assert final_cust_read.json()["data"]["status"] == "resolved"

