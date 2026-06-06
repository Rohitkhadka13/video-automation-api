# =============================================================================
# app/domain/repositories/user_repository.py
# Abstract interface for user persistence operations.
# =============================================================================
from __future__ import annotations

from abc import abstractmethod
from uuid import UUID

from app.domain.entities.user import UserEntity
from app.domain.repositories.base import SoftDeletableRepository


class IUserRepository(SoftDeletableRepository[UserEntity]):
    """
    Domain contract for user persistence.

    Implementations live in app/infrastructure/repositories/.
    Domain services depend on this interface, not on SQLAlchemy.
    """

    @abstractmethod
    async def get_by_email(self, email: str) -> UserEntity | None:
        """
        Retrieve a user by email address (case-insensitive).

        Returns:
            UserEntity if found and not soft-deleted, None otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_email_include_inactive(self, email: str) -> UserEntity | None:
        """
        Retrieve a user by email regardless of is_active status.
        Used by admin tools and account recovery flows.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_active_by_id(self, user_id: UUID) -> UserEntity | None:
        """
        Retrieve a user by ID only if they are active and not deleted.
        Used by JWT validation — inactive users cannot authenticate.
        """
        raise NotImplementedError

    @abstractmethod
    async def email_exists(self, email: str) -> bool:
        """
        Check whether an email address is already registered.
        More efficient than get_by_email() when we only need a boolean.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_password(self, user_id: UUID, hashed_password: str) -> bool:
        """
        Update the hashed_password field for a user.

        Returns:
            True on success, False if user_id not found.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_refresh_token_family(
        self, user_id: UUID, new_family: str
    ) -> bool:
        """
        Rotate the refresh_token_family, invalidating all existing refresh tokens.

        Returns:
            True on success, False if user_id not found.
        """
        raise NotImplementedError

    @abstractmethod
    async def set_active(self, user_id: UUID, is_active: bool) -> bool:
        """
        Activate or deactivate a user account.

        Returns:
            True on success, False if user_id not found.
        """
        raise NotImplementedError

    @abstractmethod
    async def set_verified(self, user_id: UUID, is_verified: bool) -> bool:
        """
        Mark a user's email as verified.

        Returns:
            True on success, False if user_id not found.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_role(
        self,
        role: str,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[UserEntity]:
        """Return paginated list of users with a specific role."""
        raise NotImplementedError

    @abstractmethod
    async def count_active(self) -> int:
        """Return count of active, non-deleted users."""
        raise NotImplementedError