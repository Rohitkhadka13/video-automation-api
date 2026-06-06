# =============================================================================
# app/api/v1/endpoints/auth.py
# Authentication endpoints: login, token refresh, logout.
# =============================================================================
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status,Response

from app.api.deps import CurrentUser, get_auth_service
from app.core.config import settings
from app.core.exceptions import AuthenticationError, ExpiredTokenError, InvalidTokenError
from app.core.logging import get_logger
from app.domain.services.auth_service import AuthService
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshRequest, TokenResponse
from app.schemas.user import UserRead

router = APIRouter()
logger = get_logger(__name__)

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and receive JWT tokens",
    responses={
        401: {"description": "Invalid credentials or account inactive"},
    },
)
async def login(
    body: LoginRequest,
    auth_service: AuthServiceDep,
) -> TokenResponse:
    """
    Authenticate with email + password.

    Returns an access token (short-lived) and a refresh token (long-lived).
    Include the access token in subsequent requests:
    `Authorization: Bearer <access_token>`
    """
    try:
        _user, tokens = await auth_service.login(body.email, body.password)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange a refresh token for a new token pair",
    responses={
        401: {"description": "Refresh token expired or invalid"},
    },
)
async def refresh(
    body: RefreshRequest,
    auth_service: AuthServiceDep,
) -> TokenResponse:
    """
    Exchange a valid refresh token for a new access + refresh token pair.

    The submitted refresh token is invalidated after use (rotation).
    Store the new refresh token from the response for subsequent refreshes.
    """
    try:
        _user, tokens = await auth_service.refresh_tokens(body.refresh_token)
    except ExpiredTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except (InvalidTokenError, AuthenticationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Invalidate all sessions for the current user",
)
async def logout(
    current_user: CurrentUser,
    auth_service: AuthServiceDep,
    body: LogoutRequest | None = None,
) -> Response:
    """
    Invalidate all refresh tokens for the current user.

    This rotates the token family, making all existing refresh tokens
    immediately invalid. The client should discard all stored tokens.
    """
    await auth_service.logout(current_user.id)
    logger.info("auth.logout", user_id=str(current_user.id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get the currently authenticated user",
)
async def get_me(current_user: CurrentUser) -> UserRead:
    """Return the profile of the currently authenticated user."""
    return UserRead(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        avatar_url=current_user.avatar_url,
        bio=current_user.bio,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )