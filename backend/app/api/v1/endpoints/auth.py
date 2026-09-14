"""
app/api/v1/endpoints/auth.py

Authentication API endpoints.

Endpoints:
  POST /api/v1/auth/register  — Create new account
  POST /api/v1/auth/login     — Authenticate and get tokens
  POST /api/v1/auth/refresh   — Refresh access token
  GET  /api/v1/auth/me        — Get current user profile
  POST /api/v1/auth/logout    — Logout (client-side token discard)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.auth.dependencies import get_current_active_user
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.services.auth_service import (
    AuthenticationError,
    RegistrationError,
    authenticate_user,
    refresh_access_token,
    register_user,
)
from app.utils.responses import error_response, success_response

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = get_logger(__name__)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    response_description="JWT tokens and user info",
)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user with email, password, and role.

    Returns access and refresh tokens on success.
    """
    try:
        user, tokens = await register_user(payload, db)
        return success_response(
            data={
                "user": UserResponse.model_validate(user).model_dump(mode="json"),
                "tokens": tokens.model_dump(),
            },
            message="Account created successfully",
            status_code=201,
        )
    except RegistrationError as exc:
        return error_response(message=str(exc), status_code=409)
    except Exception as exc:
        logger.error(f"Registration error: {exc}", exc_info=True)
        return error_response(message="Registration failed", status_code=500)


@router.post(
    "/login",
    summary="Login with email and password",
    response_description="JWT access and refresh tokens",
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate a user and return JWT tokens.
    """
    try:
        user, tokens = await authenticate_user(payload, db)
        return success_response(
            data={
                "user": UserResponse.model_validate(user).model_dump(mode="json"),
                "tokens": tokens.model_dump(),
            },
            message="Login successful",
        )
    except AuthenticationError as exc:
        return error_response(message=str(exc), status_code=401)
    except Exception as exc:
        logger.error(f"Login error: {exc}", exc_info=True)
        return error_response(message="Login failed", status_code=500)


@router.post(
    "/refresh",
    summary="Refresh access token",
    response_description="New access token",
)
async def refresh(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange a valid refresh token for a new access token.
    """
    try:
        token = await refresh_access_token(payload, db)
        return success_response(
            data=token.model_dump(),
            message="Token refreshed successfully",
        )
    except AuthenticationError as exc:
        return error_response(message=str(exc), status_code=401)


@router.get(
    "/me",
    summary="Get current user profile",
    response_description="Authenticated user info",
)
async def me(
    current_user: User = Depends(get_current_active_user),
):
    """
    Returns the currently authenticated user's profile.
    Requires a valid Bearer access token.
    """
    return success_response(
        data=UserResponse.model_validate(current_user).model_dump(mode="json"),
        message="User profile retrieved",
    )


@router.post(
    "/logout",
    summary="Logout (invalidate client-side tokens)",
)
async def logout(
    current_user: User = Depends(get_current_active_user),
):
    """
    Logout endpoint.

    Note: JWT tokens are stateless — actual invalidation happens
    on the client side (clear localStorage). This endpoint is
    provided for API completeness and future server-side blacklisting.
    """
    logger.info(f"User logged out: {current_user.email}")
    return success_response(message="Logged out successfully")
