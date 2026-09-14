"""
app/agents/tools/refund_tools.py

Tools for return/refund queries.
"""

from __future__ import annotations

import asyncio
from typing import Any

from langchain_core.tools import tool

from app.core.logging import get_logger

logger = get_logger(__name__)


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def _get_return_status_async(order_number: str, user_id: str) -> dict[str, Any]:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app.config.settings import get_settings
    from app.models.order import Order
    from app.models.return_model import Return
    from app.models.customer import Customer

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with async_session() as session:
            # Verify customer
            cust_result = await session.execute(
                select(Customer).where(Customer.user_id == user_id)
            )
            customer = cust_result.scalar_one_or_none()
            if not customer:
                customer = Customer(user_id=user_id)
                session.add(customer)
                await session.commit()
                await session.refresh(customer)

            # Find order
            order_result = await session.execute(
                select(Order).where(
                    Order.order_number == order_number.upper(),
                    Order.customer_id == customer.id,
                )
            )
            order = order_result.scalar_one_or_none()
            if not order:
                return {"error": f"Order {order_number} not found"}

            # Find return request
            return_result = await session.execute(
                select(Return).where(Return.order_id == order.id)
            )
            ret = return_result.scalar_one_or_none()

            if not ret:
                # Check if order is eligible
                eligible_statuses = ["delivered"]
                if order.status.value in eligible_statuses:
                    return {
                        "has_return": False,
                        "order_number": order_number,
                        "order_status": order.status.value,
                        "eligible_for_return": True,
                        "message": (
                            f"Order {order_number} is eligible for return. "
                            "Go to My Orders > Request Return to start the process."
                        ),
                    }
                else:
                    return {
                        "has_return": False,
                        "order_number": order_number,
                        "order_status": order.status.value,
                        "eligible_for_return": False,
                        "message": (
                            f"Order {order_number} has status '{order.status.value}' "
                            "and is not currently eligible for return. "
                            "Returns are only available for delivered orders."
                        ),
                    }

            return {
                "has_return": True,
                "order_number": order_number,
                "return_status": ret.status.value,
                "reason": ret.reason.value,
                "refund_amount": float(ret.refund_amount) if ret.refund_amount else None,
                "description": ret.description,
                "created_at": ret.created_at.isoformat(),
                "resolved_at": ret.resolved_at.isoformat() if ret.resolved_at else None,
            }
    finally:
        await engine.dispose()


@tool
def get_return_status(order_number: str, user_id: str) -> str:
    """
    Check the return/refund status for an order.
    Use when the customer asks about returning an item, refund status, or return eligibility.

    Args:
        order_number: The order number (e.g. CF-20260801-001)
        user_id: The authenticated user's UUID string

    Returns:
        Return status and eligibility information
    """
    result = _run(_get_return_status_async(order_number, user_id))

    if "error" in result:
        return f"Error: {result['error']}"

    if not result.get("has_return"):
        return result.get("message", "No return request found for this order.")

    lines = [
        f"Return for Order {result['order_number']}:",
        f"  Status: {result['return_status'].upper()}",
        f"  Reason: {result['reason']}",
        f"  Requested: {result['created_at'][:10]}",
    ]
    if result.get("refund_amount"):
        lines.append(f"  Refund Amount: PKR {result['refund_amount']:,.0f}")
    if result.get("resolved_at"):
        lines.append(f"  Resolved: {result['resolved_at'][:10]}")
    if result.get("description"):
        lines.append(f"  Details: {result['description']}")

    return "\n".join(lines)


REFUND_TOOLS = [get_return_status]
