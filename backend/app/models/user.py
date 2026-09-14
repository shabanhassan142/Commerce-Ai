"""
app/models/user.py

User model for authentication and role-based access control.

Roles:
  - customer: End-user of the marketplace
  - support: Human support agent (can view escalations)
  - admin: Full system access (dashboard, analytics, settings)
"""

import enum
import uuid

from sqlalchemy import Boolean, Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class UserRole(str, enum.Enum):
    """User roles for RBAC."""
    CUSTOMER = "customer"
    SUPPORT = "support"
    ADMIN = "admin"


class User(Base):
    """
    User account model.

    This is the authentication model — it stores credentials and role.
    Customer-specific marketplace data (profile, orders, etc.) will be
    in the Customer model (Module 2), linked via customer_id.
    """

    __tablename__ = "users"

    # Primary Key — UUID for security (no sequential ID enumeration)
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # Identity
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Security
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Role-Based Access Control
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole", native_enum=False),
        nullable=False,
        default=UserRole.CUSTOMER,
    )

    # Account Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
