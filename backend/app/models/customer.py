"""
app/models/customer.py

Customer profile model — linked 1:1 to User.
Stores marketplace-specific data (phone, avatar, loyalty points).
"""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Customer(Base):
    """
    Marketplace customer profile.

    Linked 1:1 to User (authentication model).
    All marketplace interactions (orders, tickets, conversations)
    are tied to Customer, not User directly.
    """

    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # 1:1 link to User (auth)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Profile
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    loyalty_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    user = relationship("User", backref="customer", uselist=False, lazy="selectin")
    addresses = relationship("Address", back_populates="customer", lazy="selectin")
    orders = relationship("Order", back_populates="customer", lazy="noload")
    tickets = relationship("SupportTicket", back_populates="customer", lazy="noload")
    conversations = relationship("Conversation", back_populates="customer", lazy="noload")

    def __repr__(self) -> str:
        return f"<Customer id={self.id} user_id={self.user_id}>"
