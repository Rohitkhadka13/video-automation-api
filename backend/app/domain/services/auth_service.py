# =============================================================================
# app/domain/services/auth_service.py
# Authentication domain service.
# Handles: login, token refresh, logout, token validation.
# No HTTP, no FastAPI — pure business logic.
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.exceptions import (
    AuthenticationError,
    ExpiredTokenError,
    InvalidTokenError,
    NotFoundError,
)
from app.core.logging import get_logger
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    decode_access_token,
    extract_subject,
    needs_rehash,
    verify_password,
)
from app.domain.entities.user import UserEntity
from app.domain.repositories.user_repository import IUserRepository

logger = get_logger(__name__)


@dataclass(frozen=True)
class TokenPair:
    """Value object holding an access + refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthService:
    """
    Handles all authentication flows.

    Dependencies are injected — this service never instantiates repositories
    or touches the database directly. Tests can inject mock repositories.
    """

    def __init__(self, user_repo: IUserRepository) -> None:
        self._user_repo = user_repo

    async def login(self, email: str, password: str) -> tuple[UserEntity, TokenPair]:
        """
        Authenticate a user with email + password.

        Flow:
            1. Look up user by email (includes inactive check later).
            2. Verify password against stored hash.
            3. Reject if account is inactive or unverified.
            4. Transparently rehash password if bcrypt parameters outdated.
            5. Issue access + refresh token pair.

        Returns:
            Tuple of (UserEntity, TokenPair).

        Raises:
            AuthenticationError: If credentials are wrong, account is inactive,
                                 or email is not verified.
        """
        # Use include_inactive so we can give a specific "account inactive" error
        user = await self._user_repo.get_by_email_include_inactive(email.lower().strip())

        if user is None:
            # Constant-time: still verify a dummy password to prevent timing attacks
            verify_password("__dummy__", "$2b$12$dummy.hash.to.prevent.timing.attacks.aaaa")
            raise AuthenticationError("Invalid email or password")

        if not verify_password(password, user.hashed_password):
            logger.warning("auth.login.invalid_password", email=email)
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("Account has been deactivated")

        if not user.is_verified:
            raise AuthenticationError(
                "Email address not verified. Check your inbox for a verification link."
            )

        # Transparent password rehash (if bcrypt rounds were upgraded)
        if needs_rehash(user.hashed_password):
            from app.core.security import hash_password
            new_hash = hash_password(password)
            await self._user_repo.update_password(user.id, new_hash)
            logger.info("auth.password.rehashed", user_id=str(user.id))

        tokens = self._issue_tokens(user)
        logger.info("auth.login.success", user_id=str(user.id), email=email)
        return user, tokens

    async def refresh_tokens(self, refresh_token: str) -> tuple[UserEntity, TokenPair]:
        """
        Issue a new token pair from a valid refresh token.

        Uses refresh token rotation: each use issues a new refresh token and
        invalidates the old one via the token family mechanism.

        Raises:
            ExpiredTokenError:  Refresh token has expired.
            InvalidTokenError:  Token is malformed or is an access token.
            AuthenticationError: User not found, inactive, or token family mismatch.
        """
        payload = decode_refresh_token(refresh_token)
        user_id = UUID(extract_subject(payload))

        user = await self._user_repo.get_active_by_id(user_id)
        if user is None:
            raise AuthenticationError("User not found or account deactivated")

        # Token family rotation — detect refresh token reuse attacks.
        # The family ID is embedded in the token as a claim and must match
        # the value stored in the DB. If it doesn't, someone reused an old
        # refresh token — rotate immediately to invalidate all sessions.
        token_family_claim = payload.get("family")
        if token_family_claim != user.refresh_token_family:
            logger.warning(
                "auth.refresh.family_mismatch",
                user_id=str(user_id),
                detail="Possible token reuse detected — rotating family",
            )
            await self._user_repo.update_refresh_token_family(user.id, str(__import__("uuid").uuid4()))
            raise AuthenticationError("Refresh token has been invalidated")

        # Rotate token family on each use
        import uuid
        new_family = str(uuid.uuid4())
        await self._user_repo.update_refresh_token_family(user.id, new_family)

        # Re-fetch to get the updated entity with new family
        updated_user = await self._user_repo.get_active_by_id(user.id)
        if updated_user is None:
            raise AuthenticationError("User not found after refresh")

        tokens = self._issue_tokens(updated_user)
        logger.info("auth.refresh.success", user_id=str(user_id))
        return updated_user, tokens

    async def logout(self, user_id: UUID) -> None:
        """
        Invalidate all sessions for a user by rotating the token family.
        All existing refresh tokens become invalid immediately.
        """
        import uuid
        new_family = str(uuid.uuid4())
        await self._user_repo.update_refresh_token_family(user_id, new_family)
        logger.info("auth.logout", user_id=str(user_id))

    async def get_current_user(self, access_token: str) -> UserEntity:
        """
        Validate an access token and return the authenticated user.
        Called by FastAPI's Depends(get_current_user) dependency.

        Raises:
            ExpiredTokenError:   Token has expired.
            InvalidTokenError:   Token is malformed.
            AuthenticationError: User not found or inactive.
        """
        payload = decode_access_token(access_token)
        user_id = UUID(extract_subject(payload))

        user = await self._user_repo.get_active_by_id(user_id)
        if user is None:
            raise AuthenticationError("User not found or account deactivated")

        return user

    def _issue_tokens(self, user: UserEntity) -> TokenPair:
        """Create a fresh access + refresh token pair for a user."""
        access = create_access_token(
            subject=user.id,
            extra_claims={"role": user.role, "email": user.email},
        )
        refresh = create_refresh_token(
            subject=user.id,
            extra_claims={"family": user.refresh_token_family},
        )
        return TokenPair(access_token=access, refresh_token=refresh)