# =============================================================================
# app/models/user.py
# User SQLAlchemy model.
# =============================================================================
from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, String, Text
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuditMixin, Base, SoftDeleteMixin

if TYPE_CHECKING:
    from app.model.models_project import Project


class UserRole(StrEnum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


# PostgreSQL native ENUM type — stored as a compact type, not VARCHAR
_user_role_enum = ENUM(
    *[r.value for r in UserRole],
    name="user_role",
    create_type=True,    # Alembic will CREATE TYPE user_role
)


class User(AuditMixin, SoftDeleteMixin, Base):
    """
    Represents an authenticated platform user.

    Relationships:
        projects: one-to-many — a user owns many projects.

    Security notes:
        - `hashed_password` is NEVER returned in API responses.
        - `is_active` = False blocks login without deleting the account.
        - `is_verified` = False until email verification completes.
        - Soft delete via SoftDeleteMixin — records are hidden, not dropped.
    """

    __tablename__ = "users"

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    email: Mapped[str] = mapped_column(
        String(320),       # RFC 5321 max email length
        nullable=False,
        unique=True,
        index=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    role: Mapped[str] = mapped_column(
        _user_role_enum,
        nullable=False,
        default=UserRole.USER,
        server_default=UserRole.USER,
        index=True,
    )

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------
    avatar_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------
    # Stored as a UUID string; rotating this value invalidates all
    # existing refresh tokens for the user (logout-all-devices).
    refresh_token_family: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        default=lambda: str(uuid.uuid4()),
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # ------------------------------------------------------------------
    # Composite indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
        Index("ix_users_role_active", "role", "is_active"),
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def rotate_refresh_token_family(self) -> str:
        """Invalidate all existing refresh tokens by rotating the family ID."""
        self.refresh_token_family = str(uuid.uuid4())
        return self.refresh_token_family