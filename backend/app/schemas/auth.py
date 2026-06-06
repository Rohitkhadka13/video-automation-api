# =============================================================================
# app/schemas/auth.py
# Auth request/response schemas.
# =============================================================================
from __future__ import annotations

from pydantic import EmailStr, Field

from app.schemas.common import BaseSchema


class LoginRequest(BaseSchema):
    """POST /auth/login request body."""
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseSchema):
    """Successful login/refresh response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(
        description="Access token TTL in seconds"
    )


class RefreshRequest(BaseSchema):
    """POST /auth/refresh request body."""
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseSchema):
    """POST /auth/logout request body."""
    refresh_token: str | None = Field(
        default=None,
        description="Optional: invalidate a specific refresh token family",
    )