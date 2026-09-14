"""
app/auth/jwt.py

JWT token creation and decoding for access and refresh tokens.

Token Strategy:
  - Access Token:  Short-lived (15 min default), used for API requests.
  - Refresh Token: Long-lived (7 days default), used to get new access tokens.
  - Both tokens include: user_id, email, role, token_type, jti (unique ID).

Security Notes:
  - JTI (JWT ID) is included for future token revocation support.
  - Token type ("access" | "refresh") is validated on decode.
  - Tokens are signed with HS256 using SECRET_KEY from settings.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from jose import JWTError, jwt

from app.config.settings import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

TokenType = Literal["access", "refresh"]


def create_access_token(
    user_id: str,
    email: str,
    role: str,
) -> str:
    """
    Create a short-lived JWT access token.

    Args:
        user_id: The user's UUID (as string).
        email: The user's email address.
        role: The user's role (customer | support | admin).

    Returns:
        A signed JWT access token string.
    """
    return _create_token(
        user_id=user_id,
        email=email,
        role=role,
        token_type="access",
        expire_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(
    user_id: str,
    email: str,
    role: str,
) -> str:
    """
    Create a long-lived JWT refresh token.

    Args:
        user_id: The user's UUID (as string).
        email: The user's email address.
        role: The user's role.

    Returns:
        A signed JWT refresh token string.
    """
    return _create_token(
        user_id=user_id,
        email=email,
        role=role,
        token_type="refresh",
        expire_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, expected_type: TokenType = "access") -> dict:
    """
    Decode and validate a JWT token.

    Args:
        token: The raw JWT string.
        expected_type: Expected token type ("access" or "refresh").

    Returns:
        The decoded payload dictionary.

    Raises:
        JWTError: If the token is invalid, expired, or wrong type.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        # Validate token type
        if payload.get("type") != expected_type:
            raise JWTError(
                f"Invalid token type: expected '{expected_type}', "
                f"got '{payload.get('type')}'"
            )

        return payload

    except JWTError as exc:
        logger.warning(f"JWT validation failed: {exc}")
        raise


def _create_token(
    user_id: str,
    email: str,
    role: str,
    token_type: TokenType,
    expire_delta: timedelta,
) -> str:
    """Internal helper to build and sign a JWT token."""
    now = datetime.now(tz=timezone.utc)
    expire = now + expire_delta

    payload = {
        "sub": user_id,           # Subject — user's UUID
        "email": email,
        "role": role,
        "type": token_type,
        "jti": str(uuid.uuid4()), # Unique token ID (for future revocation)
        "iat": now,               # Issued at
        "exp": expire,            # Expiry
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
