"""
app/agents/tools/order_tools.py

Tools for order-related queries.
Tools are sync wrappers around async DB calls using asyncio.run().
Each tool returns a structured dict the agent can reason over.
"""

from __future__ import annotations

import asyncio
from typing import Any

from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger

logger = get_logger(__name__)


def _run(coro):
    """Helper to run async code from sync tool context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def _get_order_by_number(order_number: str, user_id: str) -> dict[str, Any]:
    """Async helper: fetch order details from DB."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app.config.settings import get_settings
    from app.models.order import Order, OrderItem
    from app.models.customer import Customer
    from app.models.product import Product
    from app.models.payment import Payment

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with async_session() as session:
            # Find customer by user_id
            customer_result = await session.execute(
                select(Customer).where(Customer.user_id == user_id)
            )
            customer = customer_result.scalar_one_or_none()
            if not customer:
                customer = Customer(user_id=user_id)
                session.add(customer)
                await session.commit()
                await session.refresh(customer)

            # Find order
            order_result = await session.execute(
                select(Order)
                .options(
                    selectinload(Order.items).selectinload(OrderItem.product),
                    selectinload(Order.payment),
                )
                .where(
                    Order.order_number == order_number.upper(),
                    Order.customer_id == customer.id,
                )
            )
            order = order_result.scalar_one_or_none()
            if not order:
                return {"error": f"Order {order_number} not found or doesn't belong to your account"}

            items = []
            for item in order.items:
                items.append({
                    "product_name": item.product.name if item.product else "Unknown",
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price),
                    "total_price": float(item.total_price),
                    "sku": item.product.sku if item.product else "",
                })

            return {
                "order_number": order.order_number,
                "status": order.status.value,
                "total_amount": float(order.total_amount),
                "items": items,
                "item_count": len(items),
                "tracking_number": order.tracking_number,
                "estimated_delivery": order.estimated_delivery.isoformat() if order.estimated_delivery else None,
                "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
                "created_at": order.created_at.isoformat(),
                "payment_status": order.payment.status.value if order.payment else "unknown",
                "payment_method": order.payment.method.value if order.payment else "unknown",
            }
    finally:
        await engine.dispose()


async def _get_customer_orders(user_id: str, limit: int = 5) -> dict[str, Any]:
    """Async helper: list recent orders for a customer."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app.config.settings import get_settings
    from app.models.order import Order
    from app.models.customer import Customer

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with async_session() as session:
            customer_result = await session.execute(
                select(Customer).where(Customer.user_id == user_id)
            )
            customer = customer_result.scalar_one_or_none()
            if not customer:
                return {"error": "Customer profile not found"}

            orders_result = await session.execute(
                select(Order)
                .where(Order.customer_id == customer.id)
                .order_by(Order.created_at.desc())
                .limit(limit)
            )
            orders = orders_result.scalars().all()

            return {
                "orders": [
                    {
                        "order_number": o.order_number,
                        "status": o.status.value,
                        "total_amount": float(o.total_amount),
                        "created_at": o.created_at.isoformat(),
                        "tracking_number": o.tracking_number,
                    }
                    for o in orders
                ],
                "total_count": len(orders),
            }
    finally:
        await engine.dispose()


# ── LangChain Tool Definitions ────────────────────────────────────────────────

@tool
def get_order_status(order_number: str, user_id: str) -> str:
    """
    Get the status and details of a specific order by order number.
    Use this when the customer asks about a specific order (e.g. CF-20260718-042).

    Args:
        order_number: The order number (e.g. CF-20260801-001)
        user_id: The authenticated user's UUID string

    Returns:
        JSON-like string with order status, items, tracking, and payment info
    """
    result = _run(_get_order_by_number(order_number, user_id))
    if "error" in result:
        return f"Error: {result['error']}"

    lines = [
        f"Order: {result['order_number']}",
        f"Status: {result['status'].upper()}",
        f"Total: PKR {result['total_amount']:,.0f}",
        f"Items: {result['item_count']}",
        f"Payment: {result['payment_status']} via {result['payment_method']}",
        f"Placed: {result['created_at'][:10]}",
    ]
    if result.get("tracking_number"):
        lines.append(f"Tracking: {result['tracking_number']}")
    if result.get("estimated_delivery"):
        lines.append(f"Estimated Delivery: {result['estimated_delivery'][:10]}")
    if result.get("delivered_at"):
        lines.append(f"Delivered: {result['delivered_at'][:10]}")

    lines.append("\nItems ordered:")
    for item in result["items"]:
        lines.append(f"  - {item['product_name']} x{item['quantity']} @ PKR {item['unit_price']:,.0f}")

    return "\n".join(lines)


@tool
def list_recent_orders(user_id: str) -> str:
    """
    List the customer's most recent orders.
    Use this when the customer asks to see their orders without specifying a particular one.

    Args:
        user_id: The authenticated user's UUID string

    Returns:
        List of recent orders with status and amounts
    """
    result = _run(_get_customer_orders(user_id))
    if "error" in result:
        return f"Error: {result['error']}"

    if not result["orders"]:
        return "You have no orders yet."

    lines = [f"Your {len(result['orders'])} most recent orders:\n"]
    for order in result["orders"]:
        status = order["status"].upper()
        lines.append(
            f"  {order['order_number']} — {status} — "
            f"PKR {order['total_amount']:,.0f} "
            f"({order['created_at'][:10]})"
        )
        if order.get("tracking_number"):
            lines.append(f"    Tracking: {order['tracking_number']}")
    return "\n".join(lines)


# Export all tools for agent use
ORDER_TOOLS = [get_order_status, list_recent_orders]
