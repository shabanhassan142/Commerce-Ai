"""
tests/test_module8_purchase_and_chat.py

Comprehensive tests for Customer Purchase Flow (Add to Cart, Order Creation, Stock Decrement, RBAC Isolation)
and AI Chat Contract Verification.
"""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.database.session import AsyncSessionLocal, engine
from app.main import app
from app.models.customer import Customer
from app.models.order import Order
from app.models.product import Product
from app.models.user import User, UserRole
from app.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_order_creation_success_and_stock_decrement():
    """Verify customer order creation calculates totals server-side and decrements product stock."""
    await engine.dispose()
    async with AsyncSessionLocal() as db:
        # Fetch existing customer
        res_cust = await db.execute(select(Customer).limit(1))
        customer = res_cust.scalar_one()

        res_user = await db.execute(select(User).where(User.id == customer.user_id))
        user = res_user.scalar_one()

        # Fetch product with stock
        res_prod = await db.execute(select(Product).where(Product.stock > 5).limit(1))
        product = res_prod.scalar_one()

        initial_stock = product.stock
        order_qty = 2
        expected_total = float(product.price) * order_qty

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Generate token for customer
        from app.auth.jwt import create_access_token
        token = create_access_token(user_id=str(user.id), email=user.email, role=user.role.value if hasattr(user.role, "value") else str(user.role))
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "items": [
                {
                    "product_id": str(product.id),
                    "quantity": order_qty,
                }
            ],
            "shipping_address": {
                "street": "100 Market St",
                "city": "San Francisco",
                "state": "CA",
                "postal_code": "94105",
                "country": "USA",
            },
            "payment_method": "demo_card",
        }

        res = await ac.post("/api/v1/orders", json=payload, headers=headers)
        assert res.status_code == 201, f"Failed to create order: {res.text}"

        order_data = res.json()
        assert order_data["order_number"].startswith("ORD-")
        assert float(order_data["total_amount"]) == pytest.approx(expected_total, 0.01)
        assert len(order_data["items"]) == 1
        assert order_data["items"][0]["quantity"] == order_qty

    # Verify stock decremented in DB
    await engine.dispose()
    async with AsyncSessionLocal() as db:
        updated_prod = (await db.execute(select(Product).where(Product.id == product.id))).scalar_one()
        assert updated_prod.stock == initial_stock - order_qty


@pytest.mark.asyncio
async def test_order_creation_insufficient_stock():
    """Verify requesting more quantity than stock fails with HTTP 400."""
    await engine.dispose()
    async with AsyncSessionLocal() as db:
        res_cust = await db.execute(select(Customer).limit(1))
        customer = res_cust.scalar_one()

        res_user = await db.execute(select(User).where(User.id == customer.user_id))
        user = res_user.scalar_one()

        res_prod = await db.execute(select(Product).where(Product.stock > 0).limit(1))
        product = res_prod.scalar_one()
        excessive_qty = product.stock + 50

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        from app.auth.jwt import create_access_token
        token = create_access_token(user_id=str(user.id), email=user.email, role=user.role.value if hasattr(user.role, "value") else str(user.role))
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "items": [{"product_id": str(product.id), "quantity": excessive_qty}],
            "shipping_address": {
                "street": "100 Market St",
                "city": "San Francisco",
                "state": "CA",
                "postal_code": "94105",
                "country": "USA",
            },
            "payment_method": "demo_card",
        }

        res = await ac.post("/api/v1/orders", json=payload, headers=headers)
        assert res.status_code in (400, 422)


@pytest.mark.asyncio
async def test_customer_order_isolation():
    """Verify Customer A cannot view Customer B's order (HTTP 403)."""
    await engine.dispose()
    async with AsyncSessionLocal() as db:
        custs = (await db.execute(select(Customer).limit(2))).scalars().all()
        if len(custs) < 2:
            pytest.skip("Requires at least 2 customer profiles in database.")

        cust_a, cust_b = custs[0], custs[1]

        user_a = (await db.execute(select(User).where(User.id == cust_a.user_id))).scalar_one()
        user_b = (await db.execute(select(User).where(User.id == cust_b.user_id))).scalar_one()

        # Fetch an order belonging to Customer B
        order_b = (await db.execute(select(Order).where(Order.customer_id == cust_b.id))).scalars().first()
        if not order_b:
            pytest.skip("Customer B has no orders to test isolation.")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        from app.auth.jwt import create_access_token
        token_a = create_access_token(user_id=str(user_a.id), email=user_a.email, role=user_a.role.value if hasattr(user_a.role, "value") else str(user_a.role))
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Customer A tries to read Customer B's order
        res = await ac.get(f"/api/v1/orders/{order_b.id}", headers=headers_a)
        assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}"


@pytest.mark.asyncio
async def test_chat_service_payload_contract():
    """Verify ChatService returns both 'answer' and 'message' fields for frontend compatibility."""
    result = ChatService.process_message(
        user_id=str(uuid.uuid4()),
        message="What is your return policy?",
    )
    assert "answer" in result, "Missing 'answer' field in ChatService return dictionary"
    assert "message" in result, "Missing 'message' field in ChatService return dictionary"
    assert result["answer"] == result["message"]
