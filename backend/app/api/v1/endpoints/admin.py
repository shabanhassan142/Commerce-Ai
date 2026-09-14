"""
app/api/v1/endpoints/admin.py

Data-driven Admin Console API Endpoints.
All statistics, user management, order streams, inventory catalog metrics,
and analytics calculations are computed directly from real PostgreSQL records.

All routes require ADMIN role authorization.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import require_role
from app.database.session import get_db
from app.models.address import Address
from app.models.category import Category
from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderStatus
from app.models.payment import Payment, PaymentStatus
from app.models.product import Product, ProductImage
from app.models.ticket import SupportTicket, TicketPriority, TicketStatus
from app.models.user import User, UserRole
from app.schemas.admin import (
    AdminAnalyticsResponse,
    AdminDashboardStatsResponse,
    AdminOrderDetailResponse,
    AdminOrderListItem,
    AdminProductDetailResponse,
    AdminProductListItem,
    AdminUserDetailResponse,
    AdminUserListItem,
    LowStockProductSummary,
    PaginatedAdminOrdersResponse,
    PaginatedAdminProductsResponse,
    PaginatedAdminUsersResponse,
    RecentOrderSummary,
    RecentTicketSummary,
    RecentUserSummary,
)
from app.schemas.order import OrderItemResponse
from app.utils.responses import success_response

router = APIRouter(prefix="/admin", tags=["Admin Console"])


# ── 1. Admin Overview Dashboard ────────────────────────────────────────────────

@router.get(
    "/dashboard",
    response_model=AdminDashboardStatsResponse,
    summary="Data-driven admin dashboard metrics",
)
async def get_admin_dashboard(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Returns platform-wide metrics calculated directly from PostgreSQL.
    """
    # 1. Total users & customers count
    total_users_res = await db.execute(select(func.count(User.id)))
    total_users = total_users_res.scalar() or 0

    total_cust_res = await db.execute(select(func.count(Customer.id)))
    total_customers = total_cust_res.scalar() or 0

    # 2. Total products count & stock alerts
    prod_counts_res = await db.execute(
        select(
            func.count(Product.id).label("total"),
            func.count(case(((Product.stock > 0) & (Product.stock <= 5), 1))).label("low_stock"),
            func.count(case((Product.stock == 0, 1))).label("out_of_stock"),
        )
    )
    prod_row = prod_counts_res.first()
    total_products = prod_row.total if prod_row else 0
    low_stock_products_count = prod_row.low_stock if prod_row else 0
    out_of_stock_products_count = prod_row.out_of_stock if prod_row else 0

    # 3. Order metrics & total revenue
    order_counts_res = await db.execute(
        select(
            func.count(Order.id).label("total"),
            func.coalesce(func.sum(Order.total_amount), Decimal("0.00")).label("revenue"),
            func.count(case((Order.status == OrderStatus.PENDING, 1))).label("pending"),
            func.count(case((Order.status == OrderStatus.DELIVERED, 1))).label("completed"),
            func.count(case((Order.status == OrderStatus.CANCELLED, 1))).label("cancelled"),
        )
    )
    order_row = order_counts_res.first()
    total_orders = order_row.total if order_row else 0
    total_revenue = Decimal(str(order_row.revenue)) if order_row and order_row.revenue else Decimal("0.00")
    pending_orders = order_row.pending if order_row else 0
    completed_orders = order_row.completed if order_row else 0
    cancelled_orders = order_row.cancelled if order_row else 0

    # 4. Support ticket metrics
    ticket_counts_res = await db.execute(
        select(
            func.count(SupportTicket.id).label("total"),
            func.count(
                case((SupportTicket.status.in_([TicketStatus.OPEN, TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS]), 1))
            ).label("open_cnt"),
            func.count(case((SupportTicket.priority == TicketPriority.URGENT, 1))).label("urgent_cnt"),
            func.count(case((SupportTicket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]), 1))).label("resolved_cnt"),
            func.count(
                case(
                    (
                        and_(
                            SupportTicket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
                            SupportTicket.assigned_to.is_(None),
                        ),
                        1,
                    )
                )
            ).label("ai_resolved_cnt"),
            func.avg(SupportTicket.resolution_time_seconds).label("avg_res_time"),
        )
    )
    t_row = ticket_counts_res.first()
    total_tickets = t_row.total if t_row else 0
    open_tickets = t_row.open_cnt if t_row else 0
    urgent_tickets = t_row.urgent_cnt if t_row else 0
    resolved_tickets = t_row.resolved_cnt if t_row else 0
    ai_resolved_cnt = t_row.ai_resolved_cnt if t_row else 0
    avg_res_time = float(t_row.avg_res_time) if t_row and t_row.avg_res_time else None

    ai_resolution_rate = round((ai_resolved_cnt / resolved_tickets * 100), 1) if resolved_tickets > 0 else 0.0

    # 5. Recent orders stream (top 5)
    recent_orders_q = (
        select(Order)
        .options(selectinload(Order.customer).selectinload(Customer.user), selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .limit(5)
    )
    ro_res = await db.execute(recent_orders_q)
    recent_orders_raw = ro_res.scalars().all()

    recent_orders = []
    for o in recent_orders_raw:
        cust_name = o.customer.user.full_name if o.customer and o.customer.user else "Guest Customer"
        cust_email = o.customer.user.email if o.customer and o.customer.user else "N/A"
        recent_orders.append(
            RecentOrderSummary(
                id=o.id,
                order_number=o.order_number,
                customer_name=cust_name,
                customer_email=cust_email,
                total_amount=o.total_amount,
                status=o.status.value if hasattr(o.status, "value") else str(o.status),
                created_at=o.created_at,
                item_count=len(o.items) if o.items else 0,
            )
        )

    # 6. Recent registered users (top 5)
    recent_users_q = select(User).order_by(User.created_at.desc()).limit(5)
    ru_res = await db.execute(recent_users_q)
    recent_users_raw = ru_res.scalars().all()

    recent_users = []
    for u in recent_users_raw:
        # Calculate spending & orders
        user_orders_res = await db.execute(
            select(
                func.count(Order.id).label("cnt"),
                func.coalesce(func.sum(Order.total_amount), Decimal("0.00")).label("spent"),
            )
            .join(Customer, Order.customer_id == Customer.id)
            .where(Customer.user_id == u.id)
        )
        uo_row = user_orders_res.first()
        u_orders_cnt = uo_row.cnt if uo_row else 0
        u_spent = Decimal(str(uo_row.spent)) if uo_row and uo_row.spent else Decimal("0.00")

        recent_users.append(
            RecentUserSummary(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                role=u.role.value if hasattr(u.role, "value") else str(u.role),
                is_active=u.is_active,
                created_at=u.created_at,
                total_orders=u_orders_cnt,
                total_spent=u_spent,
            )
        )

    # 7. Low stock products alert stream (top 5)
    low_stock_q = (
        select(Product)
        .options(selectinload(Product.category), selectinload(Product.images))
        .where(Product.stock <= 5)
        .order_by(Product.stock.asc())
        .limit(5)
    )
    ls_res = await db.execute(low_stock_q)
    low_stock_raw = ls_res.scalars().all()

    low_stock_products = []
    for p in low_stock_raw:
        cat_name = p.category.name if p.category else None
        low_stock_products.append(
            LowStockProductSummary(
                id=p.id,
                name=p.name,
                sku=p.sku,
                brand=p.brand,
                price=p.price,
                stock=p.stock,
                category_name=cat_name,
                primary_image_url=p.primary_image_url,
            )
        )

    # 8. Recent support tickets (top 5)
    recent_t_q = (
        select(SupportTicket)
        .options(selectinload(SupportTicket.customer).selectinload(Customer.user))
        .order_by(SupportTicket.created_at.desc())
        .limit(5)
    )
    rt_res = await db.execute(recent_t_q)
    recent_t_raw = rt_res.scalars().all()

    recent_tickets = []
    for t in recent_t_raw:
        c_name = t.customer.user.full_name if t.customer and t.customer.user else "Customer"
        recent_tickets.append(
            RecentTicketSummary(
                id=t.id,
                ticket_number=t.ticket_number,
                subject=t.subject,
                customer_name=c_name,
                priority=t.priority.value if hasattr(t.priority, "value") else str(t.priority),
                status=t.status.value if hasattr(t.status, "value") else str(t.status),
                created_at=t.created_at,
            )
        )

    # 9. Distributions
    order_dist_res = await db.execute(
        select(Order.status, func.count(Order.id)).group_by(Order.status)
    )
    order_status_distribution = [
        {"name": st.value if hasattr(st, "value") else str(st), "value": count}
        for st, count in order_dist_res.all()
    ]

    ticket_dist_res = await db.execute(
        select(SupportTicket.status, func.count(SupportTicket.id)).group_by(SupportTicket.status)
    )
    ticket_status_distribution = [
        {"name": st.value if hasattr(st, "value") else str(st), "value": count}
        for st, count in ticket_dist_res.all()
    ]

    # Revenue by day (last 7 days)
    revenue_by_day = []
    now = datetime.now(timezone.utc)
    for i in range(6, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        rev_res = await db.execute(
            select(func.coalesce(func.sum(Order.total_amount), Decimal("0.00")))
            .where(Order.created_at >= day_start, Order.created_at < day_end)
        )
        day_rev = rev_res.scalar() or Decimal("0.00")
        revenue_by_day.append({
            "date": day_start.strftime("%b %d"),
            "revenue": float(day_rev),
        })

    return AdminDashboardStatsResponse(
        total_users=total_users,
        total_customers=total_customers,
        total_products=total_products,
        total_orders=total_orders,
        total_revenue=total_revenue,
        pending_orders=pending_orders,
        completed_orders=completed_orders,
        cancelled_orders=cancelled_orders,
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        urgent_tickets=urgent_tickets,
        resolved_tickets=resolved_tickets,
        ai_resolution_rate=ai_resolution_rate,
        average_resolution_time_seconds=avg_res_time,
        low_stock_products_count=low_stock_products_count,
        out_of_stock_products_count=out_of_stock_products_count,
        recent_orders=recent_orders,
        recent_users=recent_users,
        low_stock_products=low_stock_products,
        recent_tickets=recent_tickets,
        order_status_distribution=order_status_distribution,
        ticket_status_distribution=ticket_status_distribution,
        revenue_by_day=revenue_by_day,
    )


# ── 2. Admin Users Management ─────────────────────────────────────────────────

@router.get(
    "/users",
    response_model=PaginatedAdminUsersResponse,
    summary="List platform users with filtering and search",
)
async def list_admin_users(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN)),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search by name or email"),
    role_filter: str | None = Query(None, alias="role", description="Filter by role"),
    status_filter: str | None = Query(None, alias="status", description="Filter active/inactive"),
):
    query = select(User)

    if search:
        query = query.where(
            (User.full_name.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%"))
        )

    if role_filter:
        query = query.where(User.role == role_filter)

    if status_filter is not None:
        if status_filter.lower() == "active":
            query = query.where(User.is_active == True)  # noqa: E712
        elif status_filter.lower() == "inactive":
            query = query.where(User.is_active == False)  # noqa: E712

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_q)
    total = total_res.scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    query = query.order_by(User.created_at.desc()).offset(offset).limit(per_page)
    users_res = await db.execute(query)
    users = users_res.scalars().all()

    items = []
    for u in users:
        # Fetch associated customer if exists
        c_res = await db.execute(select(Customer).where(Customer.user_id == u.id))
        customer = c_res.scalar_one_or_none()

        total_orders = 0
        total_spent = Decimal("0.00")
        total_tickets = 0
        open_tickets = 0

        if customer:
            # Calculate orders & spend
            o_res = await db.execute(
                select(
                    func.count(Order.id).label("cnt"),
                    func.coalesce(func.sum(Order.total_amount), Decimal("0.00")).label("spent"),
                ).where(Order.customer_id == customer.id)
            )
            o_row = o_res.first()
            total_orders = o_row.cnt if o_row else 0
            total_spent = Decimal(str(o_row.spent)) if o_row and o_row.spent else Decimal("0.00")

            # Calculate tickets
            t_res = await db.execute(
                select(
                    func.count(SupportTicket.id).label("cnt"),
                    func.count(
                        case(
                            (
                                SupportTicket.status.in_(
                                    [TicketStatus.OPEN, TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS]
                                ),
                                1,
                            )
                        )
                    ).label("open_cnt"),
                ).where(SupportTicket.customer_id == customer.id)
            )
            t_row = t_res.first()
            total_tickets = t_row.cnt if t_row else 0
            open_tickets = t_row.open_cnt if t_row else 0

        items.append(
            AdminUserListItem(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                role=u.role.value if hasattr(u.role, "value") else str(u.role),
                is_active=u.is_active,
                is_verified=u.is_verified,
                created_at=u.created_at,
                customer_id=customer.id if customer else None,
                phone=customer.phone if customer else None,
                total_orders=total_orders,
                total_spent=total_spent,
                total_tickets=total_tickets,
                open_tickets=open_tickets,
            )
        )

    return PaginatedAdminUsersResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 1,
    )


@router.get(
    "/users/{user_id}",
    response_model=AdminUserDetailResponse,
    summary="Get user profile detail with order history & tickets",
)
async def get_admin_user_detail(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN)),
):
    u_res = await db.execute(select(User).where(User.id == user_id))
    user = u_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

    c_res = await db.execute(
        select(Customer)
        .where(Customer.user_id == user.id)
        .options(selectinload(Customer.addresses))
    )
    customer = c_res.scalar_one_or_none()

    orders_list = []
    tickets_list = []
    addresses_list = []
    total_orders = 0
    total_spent = Decimal("0.00")
    total_tickets = 0
    open_tickets = 0

    if customer:
        for addr in customer.addresses:
            addresses_list.append({
                "id": str(addr.id),
                "street": addr.street,
                "city": addr.city,
                "state": addr.state,
                "postal_code": addr.postal_code,
                "country": addr.country,
                "is_default": addr.is_default,
            })

        # Fetch orders
        orders_q = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.customer_id == customer.id)
            .order_by(Order.created_at.desc())
        )
        ord_res = await db.execute(orders_q)
        raw_orders = ord_res.scalars().all()

        total_orders = len(raw_orders)
        for o in raw_orders:
            total_spent += o.total_amount
            orders_list.append({
                "id": str(o.id),
                "order_number": o.order_number,
                "status": o.status.value if hasattr(o.status, "value") else str(o.status),
                "total_amount": float(o.total_amount),
                "created_at": o.created_at.isoformat(),
                "item_count": len(o.items) if o.items else 0,
            })

        # Fetch tickets
        t_q = (
            select(SupportTicket)
            .where(SupportTicket.customer_id == customer.id)
            .order_by(SupportTicket.created_at.desc())
        )
        t_res = await db.execute(t_q)
        raw_tickets = t_res.scalars().all()

        total_tickets = len(raw_tickets)
        for t in raw_tickets:
            st = t.status.value if hasattr(t.status, "value") else str(t.status)
            if st in ("open", "assigned", "in_progress", "waiting_for_customer"):
                open_tickets += 1
            tickets_list.append({
                "id": str(t.id),
                "ticket_number": t.ticket_number,
                "subject": t.subject,
                "priority": t.priority.value if hasattr(t.priority, "value") else str(t.priority),
                "status": st,
                "created_at": t.created_at.isoformat(),
            })

    return AdminUserDetailResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        customer_id=customer.id if customer else None,
        phone=customer.phone if customer else None,
        avatar_url=customer.avatar_url if customer else None,
        loyalty_points=customer.loyalty_points if customer else 0,
        shipping_addresses=addresses_list,
        total_orders=total_orders,
        total_spent=total_spent,
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        orders=orders_list,
        tickets=tickets_list,
    )


# ── 3. Admin Product Catalog Management ───────────────────────────────────────

@router.get(
    "/products",
    response_model=PaginatedAdminProductsResponse,
    summary="List product catalog with stock status & sales metrics",
)
async def list_admin_products(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN)),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search name or SKU"),
    category_slug: str | None = Query(None, description="Filter by category"),
    stock_status: str | None = Query(None, description="Filter: low_stock, out_of_stock, in_stock"),
):
    query = select(Product).options(selectinload(Product.category), selectinload(Product.images))

    if search:
        query = query.where(
            (Product.name.ilike(f"%{search}%")) | (Product.sku.ilike(f"%{search}%"))
        )

    if category_slug:
        query = query.join(Category, Product.category_id == Category.id).where(
            Category.slug == category_slug
        )

    if stock_status:
        st = stock_status.lower()
        if st == "out_of_stock":
            query = query.where(Product.stock == 0)
        elif st == "low_stock":
            query = query.where(Product.stock > 0, Product.stock <= 5)
        elif st == "in_stock":
            query = query.where(Product.stock > 0)

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_q)
    total = total_res.scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    query = query.order_by(Product.created_at.desc()).offset(offset).limit(per_page)
    prod_res = await db.execute(query)
    products = prod_res.scalars().all()

    items = []
    for p in products:
        # Compute units sold & total revenue for product
        sales_res = await db.execute(
            select(
                func.coalesce(func.sum(OrderItem.quantity), 0).label("units"),
                func.coalesce(func.sum(OrderItem.total_price), Decimal("0.00")).label("revenue"),
            ).where(OrderItem.product_id == p.id)
        )
        s_row = sales_res.first()
        units_sold = int(s_row.units) if s_row else 0
        total_rev = Decimal(str(s_row.revenue)) if s_row and s_row.revenue else Decimal("0.00")

        cat_name = p.category.name if p.category else None
        items.append(
            AdminProductListItem(
                id=p.id,
                name=p.name,
                slug=p.slug,
                sku=p.sku,
                brand=p.brand,
                category_id=p.category_id,
                category_name=cat_name,
                price=p.price,
                original_price=p.original_price,
                discount_percent=p.discount_percent,
                stock=p.stock,
                rating=p.rating,
                review_count=p.review_count,
                is_active=p.is_active,
                primary_image_url=p.primary_image_url,
                units_sold=units_sold,
                total_revenue=total_rev,
                created_at=p.created_at,
            )
        )

    return PaginatedAdminProductsResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 1,
    )


@router.get(
    "/products/{product_id}",
    response_model=AdminProductDetailResponse,
    summary="Get product detail with recent orders",
)
async def get_admin_product_detail(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN)),
):
    p_res = await db.execute(
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.category), selectinload(Product.seller), selectinload(Product.images))
    )
    p = p_res.scalar_one_or_none()
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Compute sales
    sales_res = await db.execute(
        select(
            func.coalesce(func.sum(OrderItem.quantity), 0).label("units"),
            func.coalesce(func.sum(OrderItem.total_price), Decimal("0.00")).label("revenue"),
        ).where(OrderItem.product_id == p.id)
    )
    s_row = sales_res.first()
    units_sold = int(s_row.units) if s_row else 0
    total_rev = Decimal(str(s_row.revenue)) if s_row and s_row.revenue else Decimal("0.00")

    # Fetch recent order items
    ro_q = (
        select(OrderItem)
        .options(selectinload(OrderItem.order).selectinload(Order.customer).selectinload(Customer.user))
        .where(OrderItem.product_id == p.id)
        .order_by(OrderItem.id.desc())
        .limit(10)
    )
    ro_res = await db.execute(ro_q)
    raw_items = ro_res.scalars().all()

    recent_orders = []
    for item in raw_items:
        if item.order:
            c_name = item.order.customer.user.full_name if item.order.customer and item.order.customer.user else "Customer"
            recent_orders.append({
                "order_id": str(item.order.id),
                "order_number": item.order.order_number,
                "customer_name": c_name,
                "quantity": item.quantity,
                "total_price": float(item.total_price),
                "created_at": item.order.created_at.isoformat(),
            })

    images_list = [
        {
            "id": str(img.id),
            "image_url": img.image_url,
            "alt_text": img.alt_text,
            "is_primary": img.is_primary,
            "sort_order": img.sort_order,
        }
        for img in p.images
    ]

    return AdminProductDetailResponse(
        id=p.id,
        name=p.name,
        slug=p.slug,
        sku=p.sku,
        brand=p.brand,
        description=p.description,
        category_id=p.category_id,
        category_name=p.category.name if p.category else None,
        seller_name=p.seller.name if p.seller else None,
        price=p.price,
        original_price=p.original_price,
        discount_percent=p.discount_percent,
        stock=p.stock,
        rating=p.rating,
        review_count=p.review_count,
        is_active=p.is_active,
        specifications=p.specifications,
        images=images_list,
        units_sold=units_sold,
        total_revenue=total_rev,
        recent_orders=recent_orders,
        created_at=p.created_at,
    )


# ── 4. Admin Orders Management ────────────────────────────────────────────────

@router.get(
    "/orders",
    response_model=PaginatedAdminOrdersResponse,
    summary="List all customer orders for admin",
)
async def list_admin_orders(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN)),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search by order number or customer name/email"),
    status_filter: str | None = Query(None, alias="status"),
):
    query = select(Order).options(
        selectinload(Order.customer).selectinload(Customer.user),
        selectinload(Order.items),
        selectinload(Order.payment),
    )

    if search:
        query = query.join(Customer, Order.customer_id == Customer.id).join(User, Customer.user_id == User.id).where(
            (Order.order_number.ilike(f"%{search}%"))
            | (User.full_name.ilike(f"%{search}%"))
            | (User.email.ilike(f"%{search}%"))
        )

    if status_filter:
        query = query.where(Order.status == status_filter)

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_q)
    total = total_res.scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    query = query.order_by(Order.created_at.desc()).offset(offset).limit(per_page)
    ord_res = await db.execute(query)
    orders = ord_res.scalars().all()

    items = []
    for o in orders:
        c_name = o.customer.user.full_name if o.customer and o.customer.user else "Customer"
        c_email = o.customer.user.email if o.customer and o.customer.user else "N/A"
        p_method = o.payment.method.value if o.payment and hasattr(o.payment.method, "value") else (str(o.payment.method) if o.payment else None)
        p_status = o.payment.status.value if o.payment and hasattr(o.payment.status, "value") else (str(o.payment.status) if o.payment else None)

        items.append(
            AdminOrderListItem(
                id=o.id,
                order_number=o.order_number,
                customer_id=o.customer_id,
                customer_name=c_name,
                customer_email=c_email,
                status=o.status.value if hasattr(o.status, "value") else str(o.status),
                payment_method=p_method,
                payment_status=p_status,
                total_amount=o.total_amount,
                item_count=len(o.items) if o.items else 0,
                created_at=o.created_at,
            )
        )

    return PaginatedAdminOrdersResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 1,
    )


@router.get(
    "/orders/{order_id}",
    response_model=AdminOrderDetailResponse,
    summary="Get full order detail for admin",
)
async def get_admin_order_detail(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN)),
):
    ord_res = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.customer).selectinload(Customer.user),
            selectinload(Order.shipping_address),
            selectinload(Order.items).selectinload(OrderItem.product).selectinload(Product.images),
            selectinload(Order.payment),
            selectinload(Order.return_request),
        )
    )
    o = ord_res.scalar_one_or_none()
    if not o:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Customer info
    cust_info = {
        "customer_id": str(o.customer.id) if o.customer else "",
        "user_id": str(o.customer.user.id) if o.customer and o.customer.user else "",
        "full_name": o.customer.user.full_name if o.customer and o.customer.user else "Guest",
        "email": o.customer.user.email if o.customer and o.customer.user else "N/A",
        "phone": o.customer.phone if o.customer else None,
    }

    # Address info
    addr_info = None
    if o.shipping_address:
        addr_info = {
            "street": o.shipping_address.street,
            "city": o.shipping_address.city,
            "state": o.shipping_address.state,
            "postal_code": o.shipping_address.postal_code,
            "country": o.shipping_address.country,
        }

    # Order Items
    items_resp = [OrderItemResponse.from_orm_with_product(item) for item in (o.items or [])]

    # Payment Info
    pay_info = None
    if o.payment:
        pay_info = {
            "id": str(o.payment.id),
            "amount": float(o.payment.amount),
            "method": o.payment.method.value if hasattr(o.payment.method, "value") else str(o.payment.method),
            "status": o.payment.status.value if hasattr(o.payment.status, "value") else str(o.payment.status),
            "transaction_id": o.payment.transaction_id,
            "paid_at": o.payment.paid_at.isoformat() if o.payment.paid_at else None,
        }

    # Related Tickets
    t_q = select(SupportTicket).where(SupportTicket.order_id == o.id)
    t_res = await db.execute(t_q)
    raw_tickets = t_res.scalars().all()
    tickets_list = [
        {
            "id": str(t.id),
            "ticket_number": t.ticket_number,
            "subject": t.subject,
            "status": t.status.value if hasattr(t.status, "value") else str(t.status),
            "priority": t.priority.value if hasattr(t.priority, "value") else str(t.priority),
        }
        for t in raw_tickets
    ]

    return AdminOrderDetailResponse(
        id=o.id,
        order_number=o.order_number,
        status=o.status.value if hasattr(o.status, "value") else str(o.status),
        total_amount=o.total_amount,
        tracking_number=o.tracking_number,
        estimated_delivery=o.estimated_delivery,
        delivered_at=o.delivered_at,
        notes=o.notes,
        created_at=o.created_at,
        customer=cust_info,
        shipping_address=addr_info,
        items=items_resp,
        payment=pay_info,
        return_request=o.return_request.__dict__ if o.return_request else None,
        tickets=tickets_list,
    )


@router.patch(
    "/orders/{order_id}/status",
    summary="Update order status (Admin)",
)
async def update_admin_order_status(
    order_id: uuid.UUID,
    payload: dict[str, str],
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN)),
):
    new_status = payload.get("status")
    if not new_status:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Status field is required")

    ord_res = await db.execute(select(Order).where(Order.id == order_id))
    o = ord_res.scalar_one_or_none()
    if not o:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Order not found")

    try:
        o.status = OrderStatus(new_status.lower())
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: {new_status}")

    await db.commit()
    return success_response(message=f"Order status updated to {new_status}")


# ── 5. Real-Time Platform Analytics ───────────────────────────────────────────

@router.get(
    "/analytics",
    response_model=AdminAnalyticsResponse,
    summary="Calculated platform analytics from PostgreSQL",
)
async def get_admin_analytics(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN)),
):
    # 1. Total revenue & orders
    rev_res = await db.execute(
        select(
            func.count(Order.id).label("cnt"),
            func.coalesce(func.sum(Order.total_amount), Decimal("0.00")).label("rev"),
        )
    )
    r_row = rev_res.first()
    total_orders = r_row.cnt if r_row else 0
    total_revenue = Decimal(str(r_row.rev)) if r_row and r_row.rev else Decimal("0.00")
    avg_order_val = Decimal(str(round(total_revenue / total_orders, 2))) if total_orders > 0 else Decimal("0.00")

    # 2. Revenue & Orders Trend (Last 7 Days)
    revenue_trend = []
    orders_trend = []
    now = datetime.now(timezone.utc)
    for i in range(6, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        day_res = await db.execute(
            select(
                func.count(Order.id).label("cnt"),
                func.coalesce(func.sum(Order.total_amount), Decimal("0.00")).label("rev"),
            ).where(Order.created_at >= day_start, Order.created_at < day_end)
        )
        d_row = day_res.first()
        day_cnt = d_row.cnt if d_row else 0
        day_rev = float(d_row.rev) if d_row and d_row.rev else 0.0
        
        date_str = day_start.strftime("%b %d")
        revenue_trend.append({"date": date_str, "revenue": day_rev})
        orders_trend.append({"date": date_str, "orders": day_cnt})

    # 3. Best Selling Products (Top 5 by units)
    bs_q = (
        select(
            Product.name,
            func.coalesce(func.sum(OrderItem.quantity), 0).label("units_sold"),
            func.coalesce(func.sum(OrderItem.total_price), Decimal("0.00")).label("revenue"),
        )
        .join(OrderItem, Product.id == OrderItem.product_id)
        .group_by(Product.id, Product.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
    )
    bs_res = await db.execute(bs_q)
    best_selling_products = [
        {"name": name, "units_sold": units, "revenue": float(rev)}
        for name, units, rev in bs_res.all()
    ]

    # 4. Sales by Category
    cat_q = (
        select(
            Category.name,
            func.coalesce(func.sum(OrderItem.total_price), Decimal("0.00")).label("revenue"),
        )
        .join(Product, Category.id == Product.category_id)
        .join(OrderItem, Product.id == OrderItem.product_id)
        .group_by(Category.id, Category.name)
        .order_by(func.sum(OrderItem.total_price).desc())
    )
    cat_res = await db.execute(cat_q)
    sales_by_category = [
        {"name": name, "revenue": float(rev)}
        for name, rev in cat_res.all()
    ]

    # 5. Stock status summary
    stock_res = await db.execute(
        select(
            func.count(case((Product.stock > 5, 1))).label("in_stock"),
            func.count(case(((Product.stock > 0) & (Product.stock <= 5), 1))).label("low_stock"),
            func.count(case((Product.stock == 0, 1))).label("out_of_stock"),
        )
    )
    st_row = stock_res.first()
    stock_status_summary = {
        "in_stock": st_row.in_stock if st_row else 0,
        "low_stock": st_row.low_stock if st_row else 0,
        "out_of_stock": st_row.out_of_stock if st_row else 0,
    }

    # 6. Customer Insights
    total_cust_res = await db.execute(select(func.count(Customer.id)))
    total_customers = total_cust_res.scalar() or 0

    thirty_days_ago = now - timedelta(days=30)
    new_cust_res = await db.execute(
        select(func.count(Customer.id))
        .join(User, Customer.user_id == User.id)
        .where(User.created_at >= thirty_days_ago)
    )
    new_customers_30d = new_cust_res.scalar() or 0

    # Repeat customers (customers with > 1 order)
    rep_res = await db.execute(
        select(func.count())
        .select_from(
            select(Order.customer_id)
            .group_by(Order.customer_id)
            .having(func.count(Order.id) > 1)
            .subquery()
        )
    )
    repeat_cust_cnt = rep_res.scalar() or 0
    repeat_customer_rate = round((repeat_cust_cnt / total_customers * 100), 1) if total_customers > 0 else 0.0
    avg_cust_spend = Decimal(str(round(total_revenue / total_customers, 2))) if total_customers > 0 else Decimal("0.00")

    # 7. Support Performance
    t_res = await db.execute(
        select(
            func.count(SupportTicket.id).label("total"),
            func.count(
                case((SupportTicket.status.in_([TicketStatus.OPEN, TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS]), 1))
            ).label("open_cnt"),
            func.count(case((SupportTicket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]), 1))).label("resolved_cnt"),
            func.count(
                case(
                    (
                        and_(
                            SupportTicket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
                            SupportTicket.assigned_to.is_(None),
                        ),
                        1,
                    )
                )
            ).label("ai_resolved_cnt"),
            func.avg(SupportTicket.resolution_time_seconds).label("avg_res_time"),
        )
    )
    tr_row = t_res.first()
    total_t = tr_row.total if tr_row else 0
    open_t = tr_row.open_cnt if tr_row else 0
    resolved_t = tr_row.resolved_cnt if tr_row else 0
    ai_resolved_t = tr_row.ai_resolved_cnt if tr_row else 0
    avg_res_t = float(tr_row.avg_res_time) if tr_row and tr_row.avg_res_time else None

    resolution_rate = round((resolved_t / total_t * 100), 1) if total_t > 0 else 0.0
    ai_resolution_rate = round((ai_resolved_t / resolved_t * 100), 1) if resolved_t > 0 else 0.0

    return AdminAnalyticsResponse(
        total_revenue=total_revenue,
        total_orders=total_orders,
        average_order_value=avg_order_val,
        revenue_trend=revenue_trend,
        orders_trend=orders_trend,
        best_selling_products=best_selling_products,
        sales_by_category=sales_by_category,
        stock_status_summary=stock_status_summary,
        total_customers=total_customers,
        new_customers_30d=new_customers_30d,
        repeat_customer_rate=repeat_customer_rate,
        average_customer_spend=avg_cust_spend,
        total_tickets=total_t,
        open_tickets=open_t,
        resolution_rate=resolution_rate,
        ai_resolution_rate=ai_resolution_rate,
        average_resolution_time_seconds=avg_res_t,
    )
