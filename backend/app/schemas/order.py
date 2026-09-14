"""
app/schemas/order.py

Pydantic schemas for Order-related API responses.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class OrderItemCreate(BaseModel):
    """Line item in order creation request."""
    product_id: uuid.UUID
    quantity: int = Field(..., ge=1, le=100, description="Quantity to purchase")


class ShippingAddressCreate(BaseModel):
    """Shipping address details for demo order placement."""
    street: str = Field(..., min_length=3, max_length=255)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    postal_code: str = Field(..., min_length=2, max_length=20)
    country: str = Field(..., min_length=2, max_length=100)


class OrderCreateRequest(BaseModel):
    """Order placement payload."""
    items: list[OrderItemCreate] = Field(..., min_length=1)
    shipping_address: ShippingAddressCreate
    payment_method: str = Field("demo_card", description="Demo payment method label")


class OrderItemResponse(BaseModel):
    """Order line item in API responses."""
    id: uuid.UUID
    product_id: uuid.UUID | None
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    product_name: str | None = None
    product_image: str | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_product(cls, item) -> "OrderItemResponse":
        """Build response including product info."""
        return cls(
            id=item.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price,
            product_name=item.product.name if item.product else None,
            product_image=item.product.image_url if item.product else None,
        )


class PaymentResponse(BaseModel):
    """Payment info in API responses."""
    id: uuid.UUID
    method: str
    status: str
    amount: Decimal
    transaction_id: str | None = None
    paid_at: datetime | None = None

    model_config = {"from_attributes": True}


class ReturnResponse(BaseModel):
    """Return request in API responses."""
    id: uuid.UUID
    reason: str
    status: str
    refund_amount: Decimal | None = None
    description: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    """Full order detail in API responses."""
    id: uuid.UUID
    order_number: str
    status: str
    total_amount: Decimal
    tracking_number: str | None = None
    estimated_delivery: datetime | None = None
    delivered_at: datetime | None = None
    notes: str | None = None
    created_at: datetime
    items: list[OrderItemResponse] = []
    payment: PaymentResponse | None = None
    return_request: ReturnResponse | None = None

    model_config = {"from_attributes": True}


class OrderListItem(BaseModel):
    """Compact order for list views."""
    id: uuid.UUID
    order_number: str
    status: str
    total_amount: Decimal
    created_at: datetime
    item_count: int = 0

    model_config = {"from_attributes": True}
