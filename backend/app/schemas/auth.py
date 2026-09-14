"""
app/schemas/auth.py

Pydantic v2 schemas for authentication request/response payloads.
"""

import uuid
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


# ── Request Schemas ───────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Payload for POST /auth/register"""

    full_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        examples=["Alice Johnson"],
    )
    email: EmailStr = Field(
        ...,
        examples=["alice@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        examples=["SecurePass123!"],
    )
    role: UserRole = Field(
        default=UserRole.CUSTOMER,
        examples=["customer"],
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Enforce minimum password complexity."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        return v.strip()


class LoginRequest(BaseModel):
    """Payload for POST /auth/login"""

    email: EmailStr = Field(..., examples=["alice@example.com"])
    password: str = Field(..., examples=["SecurePass123!"])


class RefreshRequest(BaseModel):
    """Payload for POST /auth/refresh"""

    refresh_token: str = Field(..., description="A valid refresh JWT token")


# ── Response Schemas ──────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """Response for login and register endpoints."""

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Access token TTL in seconds")


class AccessTokenResponse(BaseModel):
    """Response for token refresh endpoint."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
