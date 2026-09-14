"""
app/models/return_model.py

Return/refund request model.
Named 'return_model.py' because 'return' is a Python reserved keyword.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ReturnReason(str, enum.Enum):
    """Reasons for return."""
    DAMAGED = "damaged"
    WRONG_ITEM = "wrong_item"
    NOT_AS_DESCRIBED = "not_as_described"
    CHANGED_MIND = "changed_mind"
    DEFECTIVE = "defective"


class ReturnStatus(str, enum.Enum):
    """Return request lifecycle."""
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    REFUNDED = "refunded"
    COMPLETED = "completed"


class Return(Base):
    """Return/refund request for an order."""

    __tablename__ = "returns"

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

    reason: Mapped[ReturnReason] = mapped_column(
        Enum(ReturnReason, name="returnreason", native_enum=False),
        nullable=False,
    )

    status: Mapped[ReturnStatus] = mapped_column(
        Enum(ReturnStatus, name="returnstatus", native_enum=False),
        nullable=False,
        default=ReturnStatus.REQUESTED,
    )

    refund_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    order = relationship("Order", back_populates="return_request")

    def __repr__(self) -> str:
        return f"<Return id={self.id} reason={self.reason} status={self.status}>"
