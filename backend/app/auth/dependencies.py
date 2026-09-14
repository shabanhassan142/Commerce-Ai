"""
app/auth/dependencies.py

FastAPI dependency injectors for authentication and authorization.

Provides:
  - get_current_user(): Validates JWT and returns the authenticated User.
  - get_current_active_user(): Ensures the user account is active.
  - require_role(): Factory that creates role-based access guards.

Usage in route handlers:
    @router.get("/admin")
    async def admin_only(
        user: User = Depends(require_role(UserRole.ADMIN))
    ):
        ...
"""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.auth.jwt import decode_token
from app.core.logging import get_logger
from app.models.user import User, UserRole

logger = get_logger(__name__)

# Bearer token extractor — reads "Authorization: Bearer <token>"
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ],
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validates the JWT access token and returns the authenticated User.

    Raises:
        401 UNAUTHORIZED — if token is missing, invalid, or expired.
        401 UNAUTHORIZED — if the user no longer exists in the DB.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    user_id = None
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
        user_uuid = uuid.UUID(user_id)
    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    # Fetch user from database
    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning(f"Token valid but user not found: {user_id}")
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Extends get_current_user() by also checking if the account is active.

    Raises:
        403 FORBIDDEN — if the account has been deactivated.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact support.",
        )
    return current_user


def require_role(*roles: UserRole):
    """
    Dependency factory that restricts access to specific roles.

    Args:
        *roles: One or more UserRole values that are allowed.

    Returns:
        A FastAPI dependency that raises 403 if the user's role
        is not in the allowed roles.

    Usage:
        @router.get("/admin-only")
        async def admin_route(
            user: User = Depends(require_role(UserRole.ADMIN))
        ):
            ...

        @router.get("/staff")
        async def staff_route(
            user: User = Depends(require_role(UserRole.ADMIN, UserRole.SUPPORT))
        ):
            ...
    """
    async def _role_guard(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if current_user.role not in roles:
            logger.warning(
                f"Access denied: user {current_user.id} "
                f"(role={current_user.role}) tried to access "
                f"route requiring {roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {[r.value for r in roles]}",
            )
        return current_user

    return _role_guard
