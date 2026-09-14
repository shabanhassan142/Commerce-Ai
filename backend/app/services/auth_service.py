"""
app/services/auth_service.py

Business logic for authentication operations.

Separating business logic from route handlers (Single Responsibility Principle):
  - Route handlers: Handle HTTP concerns (request parsing, response formatting)
  - Services: Handle business logic (validation, DB operations, token creation)
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token, create_refresh_token, decode_token
from app.auth.password import hash_password, verify_password
from app.config.settings import get_settings
from app.core.logging import get_logger
from app.models.user import User, UserRole
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)

settings = get_settings()
logger = get_logger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class RegistrationError(Exception):
    """Raised when registration fails (e.g., email already exists)."""
    pass


async def register_user(
    payload: RegisterRequest,
    db: AsyncSession,
) -> tuple[User, TokenResponse]:
    """
    Register a new user account.

    Steps:
      1. Check if email is already in use.
      2. Hash the password.
      3. Create and persist the User record.
      4. Generate access + refresh tokens.

    Args:
        payload: Validated RegisterRequest with name, email, password, role.
        db: Active async DB session.

    Returns:
        Tuple of (User, TokenResponse).

    Raises:
        RegistrationError: If the email is already registered.
    """
    # Check for duplicate email
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise RegistrationError(f"Email '{payload.email}' is already registered")

    # Create user record
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.flush()  # Get the generated UUID without committing
    await db.refresh(user)

    logger.info(f"New user registered: {user.email} (role={user.role})")

    # Auto-create Customer profile for customer accounts
    if user.role == UserRole.CUSTOMER or str(user.role).lower() == "customer":
        from app.models.customer import Customer
        customer = Customer(user_id=user.id)
        db.add(customer)
        await db.flush()

    tokens = _build_token_response(user)
    return user, tokens


async def authenticate_user(
    payload: LoginRequest,
    db: AsyncSession,
) -> tuple[User, TokenResponse]:
    """
    Authenticate a user by email and password.

    Args:
        payload: Validated LoginRequest with email and password.
        db: Active async DB session.

    Returns:
        Tuple of (User, TokenResponse).

    Raises:
        AuthenticationError: If credentials are invalid or account is inactive.
    """
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    # Use consistent error message to avoid email enumeration attacks
    _auth_error = AuthenticationError("Invalid email or password")

    if user is None:
        logger.warning(f"Login failed: email not found ({payload.email})")
        raise _auth_error

    if not verify_password(payload.password, user.hashed_password):
        logger.warning(f"Login failed: wrong password for {payload.email}")
        raise _auth_error

    if not user.is_active:
        raise AuthenticationError("Account is deactivated. Contact support.")

    logger.info(f"User logged in: {user.email}")
    tokens = _build_token_response(user)
    return user, tokens


async def refresh_access_token(
    payload: RefreshRequest,
    db: AsyncSession,
) -> AccessTokenResponse:
    """
    Issue a new access token using a valid refresh token.

    Args:
        payload: RefreshRequest containing the refresh token.
        db: Active async DB session.

    Returns:
        AccessTokenResponse with new access token.

    Raises:
        AuthenticationError: If refresh token is invalid or user not found.
    """
    from jose import JWTError

    try:
        token_data = decode_token(payload.refresh_token, expected_type="refresh")
    except JWTError as exc:
        raise AuthenticationError(f"Invalid refresh token: {exc}") from exc

    user_id = token_data.get("sub")
    try:
        user_uuid = uuid.UUID(user_id) if user_id else None
    except (ValueError, TypeError):
        raise AuthenticationError("Invalid user ID in token")

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise AuthenticationError("User not found or inactive")

    new_access_token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
    )

    logger.info(f"Access token refreshed for user: {user.email}")

    return AccessTokenResponse(
        access_token=new_access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def _build_token_response(user: User) -> TokenResponse:
    """Build a TokenResponse for a given user."""
    access_token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
    )
    refresh_token = create_refresh_token(
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
