"""
app/schemas/product.py

Pydantic schemas for Product-related API responses.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, computed_field


class CategoryResponse(BaseModel):
    """Category in API responses."""
    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    icon: str

    model_config = {"from_attributes": True}


class SellerResponse(BaseModel):
    """Seller in API responses."""
    id: uuid.UUID
    name: str
    slug: str
    rating: float
    is_verified: bool
    city: str

    model_config = {"from_attributes": True}


class ProductImageResponse(BaseModel):
    """Single product image in API responses."""
    id: uuid.UUID
    image_url: str
    alt_text: str | None = None
    sort_order: int = 0
    is_primary: bool = False

    model_config = {"from_attributes": True}


class ProductResponse(BaseModel):
    """Full product detail in API responses."""
    id: uuid.UUID
    name: str
    slug: str
    description: str
    brand: str | None = None
    price: Decimal
    original_price: Decimal | None = None
    discount_percent: float = 0.0
    sku: str
    stock: int
    rating: float
    review_count: int
    image_url: str | None = None
    specifications: dict | None = None
    is_active: bool
    created_at: datetime
    category: CategoryResponse | None = None
    seller: SellerResponse | None = None
    images: list[ProductImageResponse] = []

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_product(cls, product) -> "ProductResponse":
        """Build response with computed discount_percent from the model property."""
        return cls(
            id=product.id,
            name=product.name,
            slug=product.slug,
            description=product.description,
            brand=product.brand,
            price=product.price,
            original_price=product.original_price,
            discount_percent=product.discount_percent,
            sku=product.sku,
            stock=product.stock,
            rating=product.rating,
            review_count=product.review_count,
            image_url=product.primary_image_url,
            specifications=product.specifications,
            is_active=product.is_active,
            created_at=product.created_at,
            category=CategoryResponse.model_validate(product.category) if product.category else None,
            seller=SellerResponse.model_validate(product.seller) if product.seller else None,
            images=[ProductImageResponse.model_validate(img) for img in product.images],
        )


class ProductListItem(BaseModel):
    """Compact product for list views."""
    id: uuid.UUID
    name: str
    slug: str
    price: Decimal
    original_price: Decimal | None = None
    discount_percent: float = 0.0
    brand: str | None = None
    rating: float
    review_count: int
    image_url: str | None = None
    stock: int
    category: CategoryResponse | None = None
    seller: SellerResponse | None = None
    images: list[ProductImageResponse] = []

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_product(cls, product) -> "ProductListItem":
        """Build list item with computed discount_percent from the model property."""
        return cls(
            id=product.id,
            name=product.name,
            slug=product.slug,
            price=product.price,
            original_price=product.original_price,
            discount_percent=product.discount_percent,
            brand=product.brand,
            rating=product.rating,
            review_count=product.review_count,
            image_url=product.primary_image_url,
            stock=product.stock,
            category=CategoryResponse.model_validate(product.category) if product.category else None,
            seller=SellerResponse.model_validate(product.seller) if product.seller else None,
            images=[ProductImageResponse.model_validate(img) for img in product.images],
        )
