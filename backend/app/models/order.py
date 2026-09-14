"""
app/models/order.py

Order and OrderItem models.
An Order contains 1+ OrderItems, each referencing a Product.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class OrderStatus(str, enum.Enum):
    """Order lifecycle statuses."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Order(Base):
    """Customer purchase order."""

    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    order_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True,
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="orderstatus", native_enum=False),
        nullable=False,
        default=OrderStatus.PENDING,
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False,
    )

    shipping_address_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("addresses.id", ondelete="SET NULL"),
        nullable=True,
    )

    tracking_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    estimated_delivery: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    customer = relationship("Customer", back_populates="orders", lazy="selectin")
    items = relationship("OrderItem", back_populates="order", lazy="selectin")
    payment = relationship("Payment", back_populates="order", uselist=False, lazy="selectin")
    return_request = relationship("Return", back_populates="order", uselist=False, lazy="selectin")
    shipping_address = relationship("Address", lazy="selectin")
    tickets = relationship("SupportTicket", back_populates="order", lazy="noload")

    def __repr__(self) -> str:
        return f"<Order {self.order_number} status={self.status} total={self.total_amount}>"


class OrderItem(Base):
    """Line item within an order."""

    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items", lazy="selectin")

    def __repr__(self) -> str:
        return f"<OrderItem order={self.order_id} qty={self.quantity} total={self.total_price}>"
