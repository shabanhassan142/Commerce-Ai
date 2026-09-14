"""
app/schemas/admin.py

Schemas for Admin Console endpoints.
Includes platform overview stats, paginated users/products/orders, detail models,
and aggregated real-time analytics.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.models.user import UserRole
from app.schemas.order import OrderItemResponse


# ── Recent / Quick Summary Item Schemas ─────────────────────────────────────

class RecentOrderSummary(BaseModel):
    id: uuid.UUID
    order_number: str
    customer_name: str
    customer_email: str
    total_amount: Decimal
    status: str
    created_at: datetime
    item_count: int


class RecentUserSummary(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: boolean if False else bool
    created_at: datetime
    total_orders: int
    total_spent: Decimal


class LowStockProductSummary(BaseModel):
    id: uuid.UUID
    name: str
    sku: str
    brand: str | None = None
    price: Decimal
    stock: int
    category_name: str | None = None
    primary_image_url: str | None = None


class RecentTicketSummary(BaseModel):
    id: uuid.UUID
    ticket_number: str
    subject: str
    customer_name: str
    priority: str
    status: str
    created_at: datetime


# ── Admin Dashboard Response ──────────────────────────────────────────────────

class AdminDashboardStatsResponse(BaseModel):
    # Overall Counters
    total_users: int
    total_customers: int
    total_products: int
    total_orders: int
    total_revenue: Decimal
    pending_orders: int
    completed_orders: int
    cancelled_orders: int
    
    # Support & AI Metrics
    total_tickets: int
    open_tickets: int
    urgent_tickets: int
    resolved_tickets: int
    ai_resolution_rate: float
    average_response_time_seconds: float | None = None
    average_resolution_time_seconds: float | None = None
    
    # Stock Metrics
    low_stock_products_count: int
    out_of_stock_products_count: int

    # Recent Data Streams
    recent_orders: list[RecentOrderSummary]
    recent_users: list[RecentUserSummary]
    low_stock_products: list[LowStockProductSummary]
    recent_tickets: list[RecentTicketSummary]

    # Chart Distributions
    order_status_distribution: list[dict[str, Any]]
    ticket_status_distribution: list[dict[str, Any]]
    revenue_by_day: list[dict[str, Any]]


# ── Admin User Management Schemas ─────────────────────────────────────────────

class AdminUserListItem(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    customer_id: uuid.UUID | None = None
    phone: str | None = None
    total_orders: int = 0
    total_spent: Decimal = Decimal("0.00")
    total_tickets: int = 0
    open_tickets: int = 0


class PaginatedAdminUsersResponse(BaseModel):
    items: list[AdminUserListItem]
    total: int
    page: int
    per_page: int
    pages: int


class AdminUserDetailResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    customer_id: uuid.UUID | None = None
    phone: str | None = None
    avatar_url: str | None = None
    loyalty_points: int = 0
    shipping_addresses: list[dict[str, Any]] = []
    total_orders: int = 0
    total_spent: Decimal = Decimal("0.00")
    total_tickets: int = 0
    open_tickets: int = 0
    orders: list[dict[str, Any]] = []
    tickets: list[dict[str, Any]] = []


# ── Admin Product Management Schemas ──────────────────────────────────────────

class AdminProductListItem(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    sku: str
    brand: str | None = None
    category_id: uuid.UUID | None = None
    category_name: str | None = None
    price: Decimal
    original_price: Decimal | None = None
    discount_percent: float = 0.0
    stock: int
    rating: float
    review_count: int
    is_active: bool
    primary_image_url: str | None = None
    units_sold: int = 0
    total_revenue: Decimal = Decimal("0.00")
    created_at: datetime


class PaginatedAdminProductsResponse(BaseModel):
    items: list[AdminProductListItem]
    total: int
    page: int
    per_page: int
    pages: int


class AdminProductDetailResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    sku: str
    brand: str | None = None
    description: str
    category_id: uuid.UUID | None = None
    category_name: str | None = None
    seller_name: str | None = None
    price: Decimal
    original_price: Decimal | None = None
    discount_percent: float = 0.0
    stock: int
    rating: float
    review_count: int
    is_active: bool
    specifications: dict[str, Any] | None = None
    images: list[dict[str, Any]] = []
    units_sold: int = 0
    total_revenue: Decimal = Decimal("0.00")
    recent_orders: list[dict[str, Any]] = []
    created_at: datetime


# ── Admin Order Management Schemas ────────────────────────────────────────────

class AdminOrderListItem(BaseModel):
    id: uuid.UUID
    order_number: str
    customer_id: uuid.UUID
    customer_name: str
    customer_email: str
    status: str
    payment_method: str | None = None
    payment_status: str | None = None
    total_amount: Decimal
    item_count: int
    created_at: datetime


class PaginatedAdminOrdersResponse(BaseModel):
    items: list[AdminOrderListItem]
    total: int
    page: int
    per_page: int
    pages: int


class AdminOrderDetailResponse(BaseModel):
    id: uuid.UUID
    order_number: str
    status: str
    total_amount: Decimal
    tracking_number: str | None = None
    estimated_delivery: datetime | None = None
    delivered_at: datetime | None = None
    notes: str | None = None
    created_at: datetime
    
    # Customer Info
    customer: dict[str, Any]
    
    # Address Info
    shipping_address: dict[str, Any] | None = None
    
    # Line items & Payment
    items: list[OrderItemResponse] = []
    payment: dict[str, Any] | None = None
    return_request: dict[str, Any] | None = None
    tickets: list[dict[str, Any]] = []


# ── Admin Analytics Response ──────────────────────────────────────────────────

class AdminAnalyticsResponse(BaseModel):
    # Financial metrics
    total_revenue: Decimal
    total_orders: int
    average_order_value: Decimal
    revenue_trend: list[dict[str, Any]]
    orders_trend: list[dict[str, Any]]
    
    # Product & Category breakdown
    best_selling_products: list[dict[str, Any]]
    sales_by_category: list[dict[str, Any]]
    stock_status_summary: dict[str, int]
    
    # Customer Insights
    total_customers: int
    new_customers_30d: int
    repeat_customer_rate: float
    average_customer_spend: Decimal
    
    # Support Performance
    total_tickets: int
    open_tickets: int
    resolution_rate: float
    ai_resolution_rate: float
    average_response_time_seconds: float | None = None
    average_resolution_time_seconds: float | None = None
