# =============================================================================
# app/domain/services/user_service.py
# User management domain service.
# Handles: registration, profile updates, account management.
# =============================================================================
from __future__ import annotations

from uuid import UUID

from app.core.exceptions import AlreadyExistsError, NotFoundError, InsufficientPermissionsError
from app.core.logging import get_logger
from app.core.security import hash_password, verify_password
from app.domain.entities.user import UserEntity
from app.domain.repositories.user_repository import IUserRepository
from slugify import slugify

logger = get_logger(__name__)


class UserService:
    """Handles user registration and profile management."""

    def __init__(self, user_repo: IUserRepository) -> None:
        self._user_repo = user_repo

    async def register(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
    ) -> UserEntity:
        """
        Register a new user account.

        Raises:
            AlreadyExistsError: If the email address is already registered.
        """
        normalized_email = email.lower().strip()

        if await self._user_repo.email_exists(normalized_email):
            raise AlreadyExistsError(resource="User", field="email")

        user = await self._user_repo.create(
            {
                "email": normalized_email,
                "hashed_password": hash_password(password),
                "full_name": full_name.strip(),
                "is_active": True,
                # In production, set is_verified=False and send a verification email.
                # For this SaaS we auto-verify on registration.
                "is_verified": True,
                "role": "user",
            }
        )

        logger.info("user.registered", user_id=str(user.id), email=normalized_email)
        return user

    async def get_by_id(self, user_id: UUID) -> UserEntity:
        """
        Retrieve a user by ID.

        Raises:
            NotFoundError: If the user does not exist or is soft-deleted.
        """
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError(resource="User", identifier=str(user_id))
        return user

    async def update_profile(
        self,
        user_id: UUID,
        *,
        full_name: str | None = None,
        bio: str | None = None,
        avatar_url: str | None = None,
    ) -> UserEntity:
        """
        Update user profile fields. Only provided fields are changed.

        Raises:
            NotFoundError: If the user does not exist.
        """
        update_data: dict = {}
        if full_name is not None:
            update_data["full_name"] = full_name.strip()
        if bio is not None:
            update_data["bio"] = bio.strip() or None
        if avatar_url is not None:
            update_data["avatar_url"] = avatar_url or None

        if not update_data:
            return await self.get_by_id(user_id)

        user = await self._user_repo.update(user_id, update_data)
        if user is None:
            raise NotFoundError(resource="User", identifier=str(user_id))

        logger.info("user.profile.updated", user_id=str(user_id), fields=list(update_data.keys()))
        return user

    async def change_password(
        self,
        user_id: UUID,
        *,
        current_password: str,
        new_password: str,
    ) -> None:
        """
        Change a user's password after verifying the current one.

        Raises:
            NotFoundError:       If the user does not exist.
            AuthenticationError: If current_password is wrong.
        """
        from app.core.exceptions import AuthenticationError

        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError(resource="User", identifier=str(user_id))

        if not verify_password(current_password, user.hashed_password):
            raise AuthenticationError("Current password is incorrect")

        new_hash = hash_password(new_password)
        await self._user_repo.update_password(user_id, new_hash)
        logger.info("user.password.changed", user_id=str(user_id))

    async def deactivate(self, user_id: UUID, *, requesting_user_id: UUID) -> None:
        """
        Deactivate a user account. Only admins can deactivate other users.

        Raises:
            NotFoundError:              If target user not found.
            InsufficientPermissionsError: If non-admin tries to deactivate another user.
        """
        if user_id != requesting_user_id:
            requester = await self._user_repo.get_by_id(requesting_user_id)
            if requester is None or not requester.is_admin:
                raise InsufficientPermissionsError(
                    "Only admins can deactivate other users"
                )

        success = await self._user_repo.set_active(user_id, False)
        if not success:
            raise NotFoundError(resource="User", identifier=str(user_id))

        logger.info(
            "user.deactivated",
            target_user_id=str(user_id),
            requesting_user_id=str(requesting_user_id),
        )

    async def list_users(
        self,
        *,
        requesting_user_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> list[UserEntity]:
        """
        List all users. Admin only.

        Raises:
            InsufficientPermissionsError: If the requester is not an admin.
        """
        requester = await self._user_repo.get_by_id(requesting_user_id)
        if requester is None or not requester.is_admin:
            raise InsufficientPermissionsError("Admin access required")

        return await self._user_repo.get_all(skip=skip, limit=limit)