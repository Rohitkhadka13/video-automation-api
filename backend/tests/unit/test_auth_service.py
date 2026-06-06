# =============================================================================
# tests/unit/test_auth_service.py
# Unit tests for AuthService — all DB calls mocked.
# =============================================================================
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import AuthenticationError, InvalidTokenError
from app.core.security import (
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.domain.entities.user import UserEntity
from app.domain.services.auth_service import AuthService, TokenPair

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(
    *,
    is_active: bool = True,
    is_verified: bool = True,
    password: str = "Testpass1!",
    role: str = "user",
) -> UserEntity:
    from datetime import datetime, UTC
    family = str(uuid4())
    return UserEntity(
        id=uuid4(),
        email="test@example.com",
        full_name="Test User",
        hashed_password=hash_password(password),
        is_active=is_active,
        is_verified=is_verified,
        role=role,
        refresh_token_family=family,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _make_auth_service(user: UserEntity | None = None) -> tuple[AuthService, MagicMock]:
    repo = MagicMock()
    repo.get_by_email_include_inactive = AsyncMock(return_value=user)
    repo.get_active_by_id = AsyncMock(return_value=user)
    repo.update_password = AsyncMock(return_value=True)
    repo.update_refresh_token_family = AsyncMock(return_value=True)
    service = AuthService(repo)
    return service, repo


# =============================================================================
# login
# =============================================================================

class TestLogin:

    async def test_valid_credentials_returns_user_and_tokens(self):
        user = _make_user()
        service, _ = _make_auth_service(user)

        result_user, tokens = await service.login("test@example.com", "Testpass1!")

        assert result_user.id == user.id
        assert isinstance(tokens, TokenPair)
        assert tokens.token_type == "bearer"
        assert len(tokens.access_token) > 0
        assert len(tokens.refresh_token) > 0

    async def test_wrong_password_raises_authentication_error(self):
        user = _make_user()
        service, _ = _make_auth_service(user)

        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            await service.login("test@example.com", "WrongPass1!")

    async def test_nonexistent_email_raises_authentication_error(self):
        service, _ = _make_auth_service(user=None)

        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            await service.login("nobody@example.com", "Testpass1!")

    async def test_inactive_account_raises_authentication_error(self):
        user = _make_user(is_active=False)
        service, _ = _make_auth_service(user)

        with pytest.raises(AuthenticationError, match="deactivated"):
            await service.login("test@example.com", "Testpass1!")

    async def test_unverified_email_raises_authentication_error(self):
        user = _make_user(is_verified=False)
        service, _ = _make_auth_service(user)

        with pytest.raises(AuthenticationError, match="not verified"):
            await service.login("test@example.com", "Testpass1!")

    async def test_rehash_called_when_needed(self):
        """If bcrypt parameters are outdated, password is rehashed transparently."""
        user = _make_user()
        service, repo = _make_auth_service(user)

        with patch("app.domain.services.auth_service.needs_rehash", return_value=True):
            with patch("app.domain.services.auth_service.hash_password",
                       return_value="new_hash") as mock_hash:
                await service.login("test@example.com", "Testpass1!")
                mock_hash.assert_called_once_with("Testpass1!")
                repo.update_password.assert_awaited_once_with(user.id, "new_hash")

    async def test_login_normalises_email_to_lowercase(self):
        user = _make_user()
        service, repo = _make_auth_service(user)

        await service.login("TEST@EXAMPLE.COM", "Testpass1!")

        repo.get_by_email_include_inactive.assert_awaited_once_with("test@example.com")


# =============================================================================
# refresh_tokens
# =============================================================================

class TestRefreshTokens:

    async def test_valid_refresh_token_returns_new_pair(self):
        user = _make_user()
        service, repo = _make_auth_service(user)

        # Issue a refresh token with the correct family
        refresh_token = create_refresh_token(
            subject=user.id,
            extra_claims={"family": user.refresh_token_family},
        )

        # After rotation, repo returns updated user with new family
        new_family = str(uuid4())
        updated_user = UserEntity(
            id=user.id, email=user.email, full_name=user.full_name,
            hashed_password=user.hashed_password, is_active=True,
            is_verified=True, role=user.role,
            refresh_token_family=new_family,
            created_at=user.created_at, updated_at=user.updated_at,
        )
        repo.get_active_by_id = AsyncMock(side_effect=[user, updated_user])

        _, new_tokens = await service.refresh_tokens(refresh_token)

        assert isinstance(new_tokens, TokenPair)
        repo.update_refresh_token_family.assert_awaited_once()

    async def test_family_mismatch_raises_authentication_error(self):
        user = _make_user()
        service, _ = _make_auth_service(user)

        # Token has a different family than the one stored in DB
        refresh_token = create_refresh_token(
            subject=user.id,
            extra_claims={"family": "old-stale-family-id"},
        )

        with pytest.raises(AuthenticationError, match="invalidated"):
            await service.refresh_tokens(refresh_token)

    async def test_expired_refresh_token_raises_error(self):
        from datetime import timedelta
        from jose import jwt
        from app.core.config import settings
        from datetime import UTC, datetime

        user = _make_user()
        service, _ = _make_auth_service(user)

        # Craft an already-expired token
        past = datetime.now(UTC) - timedelta(days=1)
        payload = {
            "sub": str(user.id),
            "type": "refresh",
            "iss": settings.JWT_ISSUER,
            "iat": past,
            "exp": past,
            "family": user.refresh_token_family,
        }
        expired_token = jwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        from app.core.exceptions import ExpiredTokenError
        with pytest.raises(ExpiredTokenError):
            await service.refresh_tokens(expired_token)


# =============================================================================
# logout
# =============================================================================

class TestLogout:

    async def test_logout_rotates_token_family(self):
        user = _make_user()
        service, repo = _make_auth_service(user)

        await service.logout(user.id)

        repo.update_refresh_token_family.assert_awaited_once()
        # Verify a NEW family was passed, not the old one
        call_args = repo.update_refresh_token_family.call_args
        assert call_args[0][0] == user.id
        assert call_args[0][1] != user.refresh_token_family


# =============================================================================
# get_current_user
# =============================================================================

class TestGetCurrentUser:

    async def test_valid_access_token_returns_user(self):
        from app.core.security import create_access_token
        user = _make_user()
        service, _ = _make_auth_service(user)

        token = create_access_token(subject=user.id)
        result = await service.get_current_user(token)

        assert result.id == user.id

    async def test_refresh_token_as_access_raises_invalid_token_error(self):
        user = _make_user()
        service, _ = _make_auth_service(user)

        refresh = create_refresh_token(subject=user.id)
        with pytest.raises(InvalidTokenError, match="Expected an access token"):
            await service.get_current_user(refresh)

    async def test_inactive_user_raises_authentication_error(self):
        from app.core.security import create_access_token
        service, repo = _make_auth_service(user=None)

        token = create_access_token(subject=uuid4())
        with pytest.raises(AuthenticationError):
            await service.get_current_user(token)