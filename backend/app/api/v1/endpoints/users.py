# =============================================================================
# app/api/v1/endpoints/users.py
# User management endpoints: register, profile CRUD, password change.
# =============================================================================
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import AdminUser, CurrentUser, Pagination, get_user_service
from app.core.exceptions import AlreadyExistsError, AuthenticationError, NotFoundError
from app.domain.services.user_service import UserService
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.user import PasswordChangeRequest, UserCreate, UserRead, UserUpdate

router = APIRouter()

UserServiceDep = Annotated[UserService, Depends(get_user_service)]


@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    responses={409: {"description": "Email already registered"}},
)
async def register(
    body: UserCreate,
    user_service: UserServiceDep,
) -> UserRead:
    """
    Register a new user account.

    Email addresses are normalised to lowercase.
    Passwords must be at least 8 characters with an uppercase letter and digit.
    """
    try:
        user = await user_service.register(
            email=body.email,
            password=body.password,
            full_name=body.full_name,
        )
    except AlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return UserRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        avatar_url=user.avatar_url,
        bio=user.bio,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get current user profile",
)
async def get_my_profile(current_user: CurrentUser) -> UserRead:
    """Return the authenticated user's profile."""
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


@router.patch(
    "/me",
    response_model=UserRead,
    summary="Update current user profile",
)
async def update_my_profile(
    body: UserUpdate,
    current_user: CurrentUser,
    user_service: UserServiceDep,
) -> UserRead:
    """Update the authenticated user's profile. Only provided fields are changed."""
    user = await user_service.update_profile(
        current_user.id,
        full_name=body.full_name,
        bio=body.bio,
        avatar_url=body.avatar_url,
    )
    return UserRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        avatar_url=user.avatar_url,
        bio=user.bio,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post(
    "/me/password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Change current user password",
    responses={
        401: {"description": "Current password is incorrect"},
    },
)
async def change_password(
    body: PasswordChangeRequest,
    current_user: CurrentUser,
    user_service: UserServiceDep,
) -> MessageResponse:
    """Change the authenticated user's password after verifying the current one."""
    try:
        await user_service.change_password(
            current_user.id,
            current_password=body.current_password,
            new_password=body.new_password,
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    return MessageResponse(message="Password updated successfully")


@router.get(
    "/",
    response_model=PaginatedResponse[UserRead],
    summary="List all users (admin only)",
)
async def list_users(
    admin_user: AdminUser,
    user_service: UserServiceDep,
    pagination: Pagination,
) -> PaginatedResponse[UserRead]:
    """Return paginated list of all users. Requires admin role."""
    users = await user_service.list_users(
        requesting_user_id=admin_user.id,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    reads = [
        UserRead(
            id=u.id, email=u.email, full_name=u.full_name, role=u.role,
            is_active=u.is_active, is_verified=u.is_verified,
            avatar_url=u.avatar_url, bio=u.bio,
            created_at=u.created_at, updated_at=u.updated_at,
        )
        for u in users
    ]
    return PaginatedResponse(
        items=reads, total=len(reads),
        skip=pagination.skip, limit=pagination.limit,
    )


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Get a user by ID (admin only)",
    responses={404: {"description": "User not found"}},
)
async def get_user(
    user_id: UUID,
    admin_user: AdminUser,
    user_service: UserServiceDep,
) -> UserRead:
    """Retrieve any user by ID. Requires admin role."""
    try:
        user = await user_service.get_by_id(user_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return UserRead(
        id=user.id, email=user.email, full_name=user.full_name, role=user.role,
        is_active=user.is_active, is_verified=user.is_verified,
        avatar_url=user.avatar_url, bio=user.bio,
        created_at=user.created_at, updated_at=user.updated_at,
    )