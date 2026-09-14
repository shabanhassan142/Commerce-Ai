"""
app/models/product.py

Product model — items listed on the marketplace.
Each product belongs to a category and is sold by a seller.
"""

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, Float, ForeignKey, Integer, JSON, Numeric, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Product(Base):
    """Marketplace product listing."""

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(300), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    original_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Legacy single image — kept for backward compat, prefer images relationship
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    specifications: Mapped[dict | None] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Foreign Keys
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sellers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    category = relationship("Category", back_populates="products", lazy="selectin")
    seller = relationship("Seller", back_populates="products", lazy="selectin")
    images = relationship(
        "ProductImage",
        back_populates="product",
        lazy="selectin",
        order_by="ProductImage.sort_order",
        cascade="all, delete-orphan",
    )
    order_items = relationship("OrderItem", back_populates="product", lazy="noload")

    @property
    def discount_percent(self) -> float:
        """Computed discount percentage from original_price vs price."""
        if self.original_price and self.original_price > self.price:
            return round(
                float((self.original_price - self.price) / self.original_price * 100), 1
            )
        return 0.0

    @property
    def effective_price(self) -> Decimal:
        """Current selling price (same as price — original_price is pre-discount)."""
        return self.price

    @property
    def primary_image_url(self) -> str | None:
        """Returns the primary image URL from the images relationship."""
        for img in self.images:
            if img.is_primary:
                return img.image_url
        if self.images:
            return self.images[0].image_url
        return self.image_url

    def __repr__(self) -> str:
        return f"<Product id={self.id} name={self.name} price={self.price}>"


class ProductImage(Base):
    """Multiple images per product for gallery display."""

    __tablename__ = "product_images"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_url: Mapped[str] = mapped_column(String(600), nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Relationship ──────────────────────────────────────────────────────────
    product = relationship("Product", back_populates="images")

    def __repr__(self) -> str:
        return f"<ProductImage product_id={self.product_id} primary={self.is_primary}>"
