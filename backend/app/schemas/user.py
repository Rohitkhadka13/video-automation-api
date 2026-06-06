# =============================================================================
# app/schemas/user.py
# User request/response schemas.
# =============================================================================
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import BaseSchema


class UserCreate(BaseSchema):
    """POST /users (registration) request body."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserRead(BaseSchema):
    """User response — never includes hashed_password."""
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    avatar_url: str | None
    bio: str | None
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseSchema):
    """PATCH /users/me request body — all fields optional."""
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    bio: str | None = Field(default=None, max_length=1000)
    avatar_url: str | None = Field(default=None, max_length=2000)


class PasswordChangeRequest(BaseSchema):
    """POST /users/me/password request body."""
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v