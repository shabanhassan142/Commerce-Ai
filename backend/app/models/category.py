"""
app/models/category.py

Product categories for the marketplace.
Examples: Electronics, Fashion, Beauty, Home & Living, etc.
"""

import uuid

from sqlalchemy import String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Category(Base):
    """Product category."""

    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str] = mapped_column(String(50), nullable=False, default="📦")

    # ── Relationships ─────────────────────────────────────────────────────────
    products = relationship("Product", back_populates="category", lazy="noload")

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name}>"
