"""
app/auth/password.py

Password hashing and verification using bcrypt directly.

Direct bcrypt implementation avoids passlib 1.7.4 compatibility bugs
with Python 3.12 and bcrypt >= 4.1.0 while maintaining full standard bcrypt security.
"""

import bcrypt

def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password using bcrypt.

    Args:
        plain_password: The raw password from the user.

    Returns:
        A bcrypt hashed string.
    """
    pwd_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a stored bcrypt hash.

    Args:
        plain_password: The raw password to verify.
        hashed_password: The stored bcrypt hash from the database.

    Returns:
        True if the password matches, False otherwise.
    """
    try:
        pwd_bytes = plain_password.encode("utf-8")
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False
