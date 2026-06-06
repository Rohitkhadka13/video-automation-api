# =============================================================================
# tests/unit/test_user_service.py
# Unit tests for UserService — all repos mocked.
# =============================================================================
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import AlreadyExistsError, AuthenticationError, NotFoundError
from app.core.security import hash_password
from app.domain.entities.user import UserEntity
from app.domain.services.user_service import UserService

pytestmark = pytest.mark.unit


def _make_user(
    email="test@example.com",
    role="user",
    is_active=True,
    password="Testpass1!",
) -> UserEntity:
    return UserEntity(
        id=uuid4(), email=email, full_name="Test User",
        hashed_password=hash_password(password),
        is_active=is_active, is_verified=True, role=role,
        refresh_token_family=str(uuid4()),
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    )


def _make_service(*, user: UserEntity | None = None, email_exists: bool = False):
    repo = MagicMock()
    repo.email_exists = AsyncMock(return_value=email_exists)
    repo.get_by_id = AsyncMock(return_value=user)
    repo.create = AsyncMock(return_value=user or _make_user())
    repo.update = AsyncMock(return_value=user)
    repo.update_password = AsyncMock(return_value=True)
    repo.set_active = AsyncMock(return_value=True)
    repo.get_all = AsyncMock(return_value=[user] if user else [])
    return UserService(repo), repo


class TestRegister:

    async def test_register_new_user_succeeds(self):
        user = _make_user()
        service, repo = _make_service(user=user, email_exists=False)

        result = await service.register(
            email="test@example.com",
            password="Testpass1!",
            full_name="Test User",
        )

        repo.create.assert_awaited_once()
        call_data = repo.create.call_args[0][0]
        assert call_data["email"] == "test@example.com"
        assert call_data["hashed_password"] != "Testpass1!"   # must be hashed
        assert call_data["is_active"] is True

    async def test_register_normalises_email_to_lowercase(self):
        user = _make_user()
        service, repo = _make_service(user=user, email_exists=False)

        await service.register(
            email="CAPS@EXAMPLE.COM",
            password="Testpass1!",
            full_name="Test",
        )

        call_data = repo.create.call_args[0][0]
        assert call_data["email"] == "caps@example.com"

    async def test_register_duplicate_email_raises_error(self):
        service, _ = _make_service(email_exists=True)

        with pytest.raises(AlreadyExistsError, match="email"):
            await service.register(
                email="exists@example.com",
                password="Testpass1!",
                full_name="Duplicate",
            )

    async def test_register_strips_full_name_whitespace(self):
        user = _make_user()
        service, repo = _make_service(user=user)

        await service.register(
            email="trim@example.com",
            password="Testpass1!",
            full_name="  Spaced Name  ",
        )

        call_data = repo.create.call_args[0][0]
        assert call_data["full_name"] == "Spaced Name"


class TestGetById:

    async def test_returns_user_when_found(self):
        user = _make_user()
        service, _ = _make_service(user=user)

        result = await service.get_by_id(user.id)
        assert result.id == user.id

    async def test_raises_not_found_when_missing(self):
        service, _ = _make_service(user=None)

        with pytest.raises(NotFoundError, match="User"):
            await service.get_by_id(uuid4())


class TestUpdateProfile:

    async def test_updates_only_provided_fields(self):
        user = _make_user()
        updated = UserEntity(
            id=user.id, email=user.email, full_name="New Name",
            hashed_password=user.hashed_password, is_active=True,
            is_verified=True, role=user.role,
            refresh_token_family=user.refresh_token_family,
            created_at=user.created_at, updated_at=datetime.now(UTC),
        )
        service, repo = _make_service(user=updated)

        result = await service.update_profile(
            user.id, full_name="New Name"
        )

        repo.update.assert_awaited_once()
        call_data = repo.update.call_args[0][1]
        assert "full_name" in call_data
        assert "bio" not in call_data   # not provided → not in update

    async def test_noop_when_no_fields_provided(self):
        user = _make_user()
        service, repo = _make_service(user=user)

        await service.update_profile(user.id)

        repo.update.assert_not_awaited()


class TestChangePassword:

    async def test_correct_current_password_updates_hash(self):
        user = _make_user(password="CurrentPass1!")
        service, repo = _make_service(user=user)

        await service.change_password(
            user.id,
            current_password="CurrentPass1!",
            new_password="NewPass2!",
        )

        repo.update_password.assert_awaited_once()
        new_hash = repo.update_password.call_args[0][1]
        assert new_hash != user.hashed_password

    async def test_wrong_current_password_raises_error(self):
        user = _make_user(password="CurrentPass1!")
        service, _ = _make_service(user=user)

        with pytest.raises(AuthenticationError, match="incorrect"):
            await service.change_password(
                user.id,
                current_password="WrongPass1!",
                new_password="NewPass2!",
            )


class TestDeactivate:

    async def test_user_can_deactivate_own_account(self):
        user = _make_user()
        service, repo = _make_service(user=user)

        await service.deactivate(user.id, requesting_user_id=user.id)
        repo.set_active.assert_awaited_once_with(user.id, False)

    async def test_admin_can_deactivate_other_user(self):
        admin = _make_user(role="admin")
        target = _make_user(email="target@example.com")
        service, repo = _make_service(user=admin)
        repo.get_by_id = AsyncMock(return_value=admin)
        repo.set_active = AsyncMock(return_value=True)

        await service.deactivate(target.id, requesting_user_id=admin.id)
        repo.set_active.assert_awaited_once_with(target.id, False)

    async def test_non_admin_cannot_deactivate_other_user(self):
        regular_user = _make_user(role="user")
        target_id = uuid4()
        service, repo = _make_service(user=regular_user)

        from app.core.exceptions import InsufficientPermissionsError
        with pytest.raises(InsufficientPermissionsError):
            await service.deactivate(target_id, requesting_user_id=regular_user.id)