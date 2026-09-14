"""
app/schemas/customer.py

Pydantic schemas for Customer-related API responses.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class AddressResponse(BaseModel):
    """Address in API responses."""
    id: uuid.UUID
    label: str
    street: str
    city: str
    state: str
    postal_code: str
    country: str
    is_default: bool

    model_config = {"from_attributes": True}


class CustomerResponse(BaseModel):
    """Customer profile in API responses."""
    id: uuid.UUID
    user_id: uuid.UUID
    phone: str | None = None
    avatar_url: str | None = None
    loyalty_points: int
    created_at: datetime
    addresses: list[AddressResponse] = []

    model_config = {"from_attributes": True}


class CustomerSummary(BaseModel):
    """Minimal customer info for embedding in other responses."""
    id: uuid.UUID
    phone: str | None = None
    loyalty_points: int

    model_config = {"from_attributes": True}
