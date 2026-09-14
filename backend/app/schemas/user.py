"""
app/schemas/user.py

Pydantic v2 schemas for User responses.
Never expose hashed_password in any response schema.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class UserResponse(BaseModel):
    """Full user response for authenticated users viewing their own profile."""

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserPublic(BaseModel):
    """Minimal user info for public display (e.g., in agent logs)."""

    id: uuid.UUID
    full_name: str
    role: UserRole

    model_config = {"from_attributes": True}
