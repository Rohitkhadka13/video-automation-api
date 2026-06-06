# =============================================================================
# app/domain/entities/user.py
# Pure domain entity — no SQLAlchemy, no FastAPI, no HTTP.
#
# Entities are immutable dataclasses that travel between layers.
# The domain service layer operates on entities, never on ORM models directly.
# This decouples business logic from persistence details.
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class UserEntity:
    """
    Immutable representation of a User in the domain layer.

    `frozen=True` means instances are hashable and cannot be accidentally
    mutated by callers. Updates produce a new entity via `dataclasses.replace()`.

    Fields shadow the ORM model but carry no SQLAlchemy state — no lazy-load
    triggers, no session binding, no `__dict__` pollution from instrumentation.
    """

    id: UUID
    email: str
    full_name: str
    hashed_password: str
    is_active: bool
    is_verified: bool
    role: str
    refresh_token_family: str
    created_at: datetime
    updated_at: datetime

    # Optional profile fields
    avatar_url: str | None = field(default=None)
    bio: str | None = field(default=None)
    deleted_at: datetime | None = field(default=None)

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def display_name(self) -> str:
        """First name extracted from full_name, falls back to email prefix."""
        parts = self.full_name.strip().split()
        if parts:
            return parts[0]
        return self.email.split("@")[0]

    # ------------------------------------------------------------------
    # Mutation helpers — produce new entities (immutability preserved)
    # ------------------------------------------------------------------

    def with_active(self, is_active: bool) -> "UserEntity":
        from dataclasses import replace
        return replace(self, is_active=is_active)

    def with_verified(self, is_verified: bool) -> "UserEntity":
        from dataclasses import replace
        return replace(self, is_verified=is_verified)

    def with_profile(
        self,
        *,
        full_name: str | None = None,
        avatar_url: str | None = None,
        bio: str | None = None,
    ) -> "UserEntity":
        from dataclasses import replace
        return replace(
            self,
            full_name=full_name if full_name is not None else self.full_name,
            avatar_url=avatar_url if avatar_url is not None else self.avatar_url,
            bio=bio if bio is not None else self.bio,
        )

    def with_new_password(self, hashed_password: str) -> "UserEntity":
        from dataclasses import replace
        return replace(self, hashed_password=hashed_password)

    def with_rotated_token_family(self, new_family: str) -> "UserEntity":
        from dataclasses import replace
        return replace(self, refresh_token_family=new_family)

    # ------------------------------------------------------------------
    # Safe representation — never include hashed_password in repr/str
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"UserEntity(id={self.id!r}, email={self.email!r}, "
            f"role={self.role!r}, is_active={self.is_active!r})"
        )