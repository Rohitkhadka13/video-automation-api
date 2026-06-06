# =============================================================================
# app/core/security.py
# JWT token creation/verification and password hashing utilities.
# This module is pure functions — no FastAPI deps, no DB calls.
# All auth logic in domain services calls this module directly.
# =============================================================================
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import (
    ExpiredTokenError,
    InvalidTokenError,
)

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
# bcrypt with 12 rounds — good balance of security vs. latency (~150ms on
# modern hardware). The deprecated_auto argument silently upgrades old hashes.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*, False otherwise."""
    return _pwd_context.verify(plain, hashed)


def needs_rehash(hashed: str) -> bool:
    """Return True if the hash was created with outdated parameters."""
    return _pwd_context.needs_update(hashed)


# ---------------------------------------------------------------------------
# Token types
# ---------------------------------------------------------------------------
class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


# ---------------------------------------------------------------------------
# JWT utilities
# ---------------------------------------------------------------------------
def _utcnow() -> datetime:
    """Return timezone-aware UTC datetime (avoids naive datetime pitfalls)."""
    return datetime.now(UTC)


def create_access_token(
    subject: str | UUID,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject:      User identifier — stored in the `sub` claim.
        extra_claims: Optional additional claims merged into the payload.

    Returns:
        Encoded JWT string.
    """
    now = _utcnow()
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": TokenType.ACCESS,
        "iss": settings.JWT_ISSUER,
        "iat": now,
        "exp": expire,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: str | UUID,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a signed JWT refresh token with a longer expiry.

    Args:
        subject:      User identifier — stored in the `sub` claim.
        extra_claims: Optional additional claims merged into the payload.

    Returns:
        Encoded JWT string.
    """
    now = _utcnow()
    expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": TokenType.REFRESH,
        "iss": settings.JWT_ISSUER,
        "iat": now,
        "exp": expire,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Validates: signature, expiry, issuer.

    Args:
        token: Raw JWT string.

    Returns:
        Decoded payload dictionary.

    Raises:
        ExpiredTokenError:  Token has expired.
        InvalidTokenError:  Token is malformed, signature invalid, or issuer wrong.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            options={"verify_aud": False},   # no audience claim in this app
        )
    except jwt.ExpiredSignatureError as exc:
        raise ExpiredTokenError("Token has expired") from exc
    except JWTError as exc:
        raise InvalidTokenError(f"Token validation failed: {exc}") from exc

    return payload


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode token and assert it is an access token.

    Raises:
        InvalidTokenError: If the token type claim is not 'access'.
    """
    payload = decode_token(token)
    if payload.get("type") != TokenType.ACCESS:
        raise InvalidTokenError("Expected an access token")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """
    Decode token and assert it is a refresh token.

    Raises:
        InvalidTokenError: If the token type claim is not 'refresh'.
    """
    payload = decode_token(token)
    if payload.get("type") != TokenType.REFRESH:
        raise InvalidTokenError("Expected a refresh token")
    return payload


def extract_subject(payload: dict[str, Any]) -> str:
    """
    Extract the subject claim from a decoded payload.

    Raises:
        InvalidTokenError: If the `sub` claim is missing or empty.
    """
    subject = payload.get("sub")
    if not subject:
        raise InvalidTokenError("Token missing subject claim")
    return str(subject)


def get_token_expiry(payload: dict[str, Any]) -> datetime:
    """Return the expiry datetime from a decoded payload."""
    exp = payload.get("exp")
    if exp is None:
        raise InvalidTokenError("Token missing expiry claim")
    return datetime.fromtimestamp(float(exp), tz=UTC)


def is_token_expired(payload: dict[str, Any]) -> bool:
    """Return True if the token expiry has passed."""
    try:
        return get_token_expiry(payload) < _utcnow()
    except InvalidTokenError:
        return True


def token_expires_in_seconds(payload: dict[str, Any]) -> int:
    """Return remaining TTL in seconds (0 if already expired)."""
    try:
        delta = get_token_expiry(payload) - _utcnow()
        return max(0, int(delta.total_seconds()))
    except InvalidTokenError:
        return 0