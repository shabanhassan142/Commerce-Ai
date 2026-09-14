"""
app/models/seller.py

Marketplace seller/vendor model.
Sellers list products on the marketplace.
"""

import uuid

from sqlalchemy import Boolean, Float, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Seller(Base):
    """Marketplace vendor/shop."""

    __tablename__ = "sellers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rating: Mapped[float] = mapped_column(Float, default=4.0, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="Pakistan")

    # ── Relationships ─────────────────────────────────────────────────────────
    products = relationship("Product", back_populates="seller", lazy="noload")

    def __repr__(self) -> str:
        return f"<Seller id={self.id} name={self.name}>"
