"""
app/api/v1/endpoints/orders.py

Order listing and detail endpoints for authenticated users.
Customers see their own orders; admins/support see all.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.database.session import get_db
from app.models.address import Address
from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderStatus
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.models.product import Product
from app.models.user import User, UserRole
from app.schemas.order import (
    OrderCreateRequest,
    OrderItemResponse,
    OrderListItem,
    OrderResponse,
)

router = APIRouter(prefix="/orders", tags=["Orders"])


async def _get_customer_for_user(db: AsyncSession, user: User) -> Customer:
    """Resolve User → Customer profile, creating one if missing."""
    result = await db.execute(
        select(Customer).where(Customer.user_id == user.id)
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        customer = Customer(user_id=user.id)
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
    return customer


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new customer order (Demo Checkout)",
)
async def create_order(
    payload: OrderCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """
    Create a new order for the authenticated customer.

    Validations & Security:
    - Verifies customer profile.
    - Validates products exist and have sufficient stock.
    - Prices are retrieved directly from the database (never trusted from client).
    - Atomically decrements product stock within a single DB transaction.
    - Records demo payment details cleanly.
    """
    customer = await _get_customer_for_user(db, user)

    if not payload.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must contain at least one item",
        )

    # 1. Create shipping address record
    addr_payload = payload.shipping_address
    shipping_addr = Address(
        customer_id=customer.id,
        street=addr_payload.street,
        city=addr_payload.city,
        state=addr_payload.state,
        postal_code=addr_payload.postal_code,
        country=addr_payload.country,
        is_default=False,
    )
    db.add(shipping_addr)
    await db.flush()

    # 2. Process order items & stock validation
    order_items_data = []
    total_amount = Decimal("0.00")

    for item_in in payload.items:
        prod_res = await db.execute(
            select(Product).where(Product.id == item_in.product_id).with_for_update()
        )
        product = prod_res.scalar_one_or_none()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID '{item_in.product_id}' not found",
            )

        if product.stock < item_in.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for '{product.name}'. Available: {product.stock}, requested: {item_in.quantity}",
            )

        unit_price = Decimal(str(product.price))
        line_total = unit_price * Decimal(item_in.quantity)
        total_amount += line_total

        # Decrement stock
        product.stock -= item_in.quantity

        order_items_data.append({
            "product": product,
            "product_id": product.id,
            "quantity": item_in.quantity,
            "unit_price": unit_price,
            "total_price": line_total,
        })

    # 3. Create Order
    order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    new_order = Order(
        order_number=order_number,
        customer_id=customer.id,
        status=OrderStatus.PENDING,
        total_amount=total_amount,
        shipping_address_id=shipping_addr.id,
        notes="Demo order placed via marketplace checkout",
    )
    db.add(new_order)
    await db.flush()

    # 4. Create OrderItems
    created_items = []
    for d in order_items_data:
        oi = OrderItem(
            order_id=new_order.id,
            product_id=d["product_id"],
            quantity=d["quantity"],
            unit_price=d["unit_price"],
            total_price=d["total_price"],
        )
        db.add(oi)
        created_items.append(oi)

    # 5. Create Demo Payment record
    method_enum = PaymentMethod.CARD
    if payload.payment_method.lower() in ("cod", "cash_on_delivery"):
        method_enum = PaymentMethod.COD

    demo_payment = Payment(
        order_id=new_order.id,
        method=method_enum,
        status=PaymentStatus.COMPLETED,
        amount=total_amount,
        transaction_id=f"DEMO_TXN_{uuid.uuid4().hex[:10].upper()}",
        paid_at=datetime.now(timezone.utc),
    )
    db.add(demo_payment)

    await db.commit()

    # 6. Re-query order with relationships for response
    fresh_res = await db.execute(
        select(Order).where(Order.id == new_order.id)
    )
    fresh_order = fresh_res.scalar_one()

    order_items_resp = [
        OrderItemResponse.from_orm_with_product(item)
        for item in (fresh_order.items or [])
    ]

    return OrderResponse(
        id=fresh_order.id,
        order_number=fresh_order.order_number,
        status=fresh_order.status.value if hasattr(fresh_order.status, "value") else fresh_order.status,
        total_amount=fresh_order.total_amount,
        tracking_number=fresh_order.tracking_number,
        estimated_delivery=fresh_order.estimated_delivery,
        delivered_at=fresh_order.delivered_at,
        notes=fresh_order.notes,
        created_at=fresh_order.created_at,
        items=order_items_resp,
        payment=fresh_order.payment,
        return_request=fresh_order.return_request,
    )



@router.get(
    "",
    response_model=dict,
    summary="List orders for current user",
)
async def list_orders(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status", description="Filter by order status"),
):
    """
    List orders for the authenticated user.
    Admins/support can see all orders.
    """
    query = select(Order)

    if user.role == UserRole.CUSTOMER:
        customer = await _get_customer_for_user(db, user)
        query = query.where(Order.customer_id == customer.id)

    if status_filter:
        query = query.where(Order.status == status_filter)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(Order.created_at.desc())

    result = await db.execute(query)
    orders = result.scalars().all()

    items = []
    for order in orders:
        items.append(OrderListItem(
            id=order.id,
            order_number=order.order_number,
            status=order.status.value if hasattr(order.status, "value") else order.status,
            total_amount=order.total_amount,
            created_at=order.created_at,
            item_count=len(order.items) if order.items else 0,
        ))

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get order details",
)
async def get_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """
    Get full order details including items, payment, and return status.
    Customers can only see their own orders.
    """
    result = await db.execute(
        select(Order).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Authorization: customers can only see their own orders
    if user.role == UserRole.CUSTOMER:
        customer = await _get_customer_for_user(db, user)
        if order.customer_id != customer.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this order",
            )

    # Build response with nested items
    order_items = []
    for item in (order.items or []):
        order_items.append(OrderItemResponse.from_orm_with_product(item))

    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        status=order.status.value if hasattr(order.status, "value") else order.status,
        total_amount=order.total_amount,
        tracking_number=order.tracking_number,
        estimated_delivery=order.estimated_delivery,
        delivered_at=order.delivered_at,
        notes=order.notes,
        created_at=order.created_at,
        items=order_items,
        payment=order.payment,
        return_request=order.return_request,
    )
