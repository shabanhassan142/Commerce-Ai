"""
app/database/base.py

SQLAlchemy declarative base and metadata.

ALL models must import from here so Alembic auto-detects them.
Import models at the bottom of this file as they are created.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.

    Provides:
      - Common `created_at` and `updated_at` timestamp columns
      - Automatic table name derivation (override __tablename__ in each model)
    """

    # Automatically set timestamps on insert and update
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )



