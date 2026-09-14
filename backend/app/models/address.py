"""
app/models/address.py

Shipping/billing addresses for customers.
Each customer can have multiple addresses with one marked as default.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Address(Base):
    """Customer shipping/billing address."""

    __tablename__ = "addresses"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    label: Mapped[str] = mapped_column(String(50), nullable=False, default="home")
    street: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="Pakistan")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    customer = relationship("Customer", back_populates="addresses")

    def __repr__(self) -> str:
        return f"<Address id={self.id} label={self.label} city={self.city}>"
