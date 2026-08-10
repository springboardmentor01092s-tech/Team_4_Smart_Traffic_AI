"""
app/core/security.py

All cryptographic operations for the authentication system:
  - Password hashing (bcrypt via passlib)
  - JWT creation and verification (python-jose)

This module is PURE — it has no FastAPI dependencies, no DB access,
and no HTTP concerns. It can be unit-tested in complete isolation.

Extension policy: Do NOT add HTTP logic here. Do NOT import models.
"""
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ─── Password Hashing ────────────────────────────────────────────────────────

_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,          # Work factor: 12 is a good balance for prod
)


def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password using bcrypt.

    Args:
        plain_password: The raw password string from the user.

    Returns:
        A bcrypt hash string safe to store in the database.
    """
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a stored bcrypt hash.

    Args:
        plain_password: The raw password provided during login.
        hashed_password: The stored bcrypt hash from the database.

    Returns:
        True if the password matches, False otherwise.
    """
    return _pwd_context.verify(plain_password, hashed_password)


# ─── JWT ─────────────────────────────────────────────────────────────────────

def create_access_token(
    subject: str,
    additional_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject: The token subject — typically the user's UUID as a string.
        additional_claims: Optional extra claims to embed (e.g. role, email).
        expires_delta: Custom expiry duration. Defaults to settings value.

    Returns:
        A signed JWT string (compact serialization).

    Token payload structure:
        {
            "sub": "<user_uuid>",
            "iat": <issued_at_unix_ts>,
            "exp": <expires_at_unix_ts>,
            "role": "<UserRole>",     # if provided in additional_claims
            ...
        }
    """
    now = datetime.now(UTC)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )

    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        **(additional_claims or {}),
    }

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    logger.debug("Access token created | sub=%s | exp=%s", subject, expire.isoformat())
    return token


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT access token.

    Args:
        token: The raw JWT string from the Authorization header.

    Returns:
        The decoded token payload as a dictionary.

    Raises:
        JWTError: If the token is invalid, expired, or tampered with.
                  Callers (dependencies) should catch this and raise HTTP 401.
    """
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    logger.debug("Token decoded | sub=%s", payload.get("sub"))
    return payload


def extract_token_subject(token: str) -> str | None:
    """
    Safely extract the 'sub' claim from a token without raising.

    Returns None if the token is invalid or expired.
    Useful for logging and diagnostic paths where hard failures are unwanted.
    """
    try:
        payload = decode_access_token(token)
        return payload.get("sub")
    except JWTError:
        return None
