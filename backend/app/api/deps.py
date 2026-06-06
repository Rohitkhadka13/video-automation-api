# =============================================================================
# app/api/deps.py
# FastAPI dependency injection providers.
# All Depends() used across endpoint files are defined here.
# =============================================================================
from __future__ import annotations

from typing import Annotated
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    ExpiredTokenError,
    InvalidTokenError,
    RateLimitExceededError,
)
from app.core.logging import bind_request_context, get_logger
from app.db.session import get_db
from app.domain.entities.user import UserEntity
from app.domain.services.auth_service import AuthService
from app.domain.services.project_service import ProjectService
from app.domain.services.task_service import TaskService
from app.domain.services.user_service import UserService
from app.infrastructure.repositories.sqlalchemy_project_repository import (
    SQLAlchemyProjectRepository,
)
from app.infrastructure.repositories.sqlalchemy_task_repository import (
    SQLAlchemyTaskRepository,
)
from app.infrastructure.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from app.infrastructure.repositories.sqlalchemy_video_repository import (
    SQLAlchemyVideoRepository,
)

logger = get_logger(__name__)

# HTTP Bearer token scheme — extracts "Authorization: Bearer <token>"
_bearer_scheme = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Type aliases for cleaner endpoint signatures
# ---------------------------------------------------------------------------
DBSession = Annotated[AsyncSession, Depends(get_db)]


# =============================================================================
# Repository dependencies
# =============================================================================

def get_user_repo(db: DBSession) -> SQLAlchemyUserRepository:
    return SQLAlchemyUserRepository(db)


def get_project_repo(db: DBSession) -> SQLAlchemyProjectRepository:
    return SQLAlchemyProjectRepository(db)


def get_video_repo(db: DBSession) -> SQLAlchemyVideoRepository:
    return SQLAlchemyVideoRepository(db)


def get_task_repo(db: DBSession) -> SQLAlchemyTaskRepository:
    return SQLAlchemyTaskRepository(db)


# =============================================================================
# Service dependencies
# =============================================================================

def get_auth_service(
    user_repo: Annotated[SQLAlchemyUserRepository, Depends(get_user_repo)],
) -> AuthService:
    return AuthService(user_repo)


def get_user_service(
    user_repo: Annotated[SQLAlchemyUserRepository, Depends(get_user_repo)],
) -> UserService:
    return UserService(user_repo)


def get_project_service(
    project_repo: Annotated[SQLAlchemyProjectRepository, Depends(get_project_repo)],
) -> ProjectService:
    return ProjectService(project_repo)


def get_task_service(
    task_repo: Annotated[SQLAlchemyTaskRepository, Depends(get_task_repo)],
    video_repo: Annotated[SQLAlchemyVideoRepository, Depends(get_video_repo)],
) -> TaskService:
    return TaskService(task_repo, video_repo)


# =============================================================================
# Authentication dependencies
# =============================================================================

async def _extract_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ],
) -> str:
    """
    Extract the raw Bearer token string from the Authorization header.
    Raises HTTP 401 if missing.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


async def get_current_user(
    token: Annotated[str, Depends(_extract_token)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserEntity:
    """
    Validate the Bearer token and return the authenticated UserEntity.

    Used by: all protected endpoints.

    Raises:
        HTTP 401: Token expired, invalid, or user not found/inactive.
    """
    try:
        user = await auth_service.get_current_user(token)
    except ExpiredTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (InvalidTokenError, AuthenticationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Enrich per-request log context with the authenticated user ID
    bind_request_context(
        request_id="",   # already set by middleware — this just adds user_id
        path="",
        method="",
        user_id=str(user.id),
    )

    return user


async def get_current_active_user(
    current_user: Annotated[UserEntity, Depends(get_current_user)],
) -> UserEntity:
    """
    Return the current user only if their account is active.
    Redundant in most flows (auth_service already checks), but explicit.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )
    return current_user


async def get_current_admin_user(
    current_user: Annotated[UserEntity, Depends(get_current_active_user)],
) -> UserEntity:
    """
    Return the current user only if they have admin role.
    Used by admin-only endpoints.

    Raises:
        HTTP 403: If user is not an admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# ---------------------------------------------------------------------------
# Type aliases for cleaner endpoint signatures
# ---------------------------------------------------------------------------
CurrentUser = Annotated[UserEntity, Depends(get_current_active_user)]
AdminUser = Annotated[UserEntity, Depends(get_current_admin_user)]


# =============================================================================
# Redis dependency (for rate limiting and caching)
# =============================================================================

_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """
    Return a shared async Redis client.
    The connection pool is created once and reused across requests.
    """
    global _redis_pool  # noqa: PLW0603
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            str(settings.REDIS_URL),
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
        )
    return _redis_pool


# =============================================================================
# Rate limiting dependency
# =============================================================================

async def rate_limit(
    request: "Request",  # type: ignore[name-defined]  # noqa: F821
    current_user: Annotated[UserEntity, Depends(get_current_user)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
) -> None:
    """
    Sliding-window rate limiter using Redis.
    Limits: RATE_LIMIT_REQUESTS_PER_MINUTE per user.

    Raises:
        HTTP 429: When the rate limit is exceeded.
    """
    if not settings.RATE_LIMIT_ENABLED:
        return

    from fastapi import Request as FastAPIRequest
    import time

    key = f"rate_limit:{current_user.id}:{int(time.time() // 60)}"

    try:
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, 70)   # 70s TTL — covers the current + partial next minute
        results = await pipe.execute()
        count = results[0]
    except Exception as exc:
        logger.warning("rate_limit.redis_error", error=str(exc))
        return   # fail open — don't block requests if Redis is unavailable

    limit = settings.RATE_LIMIT_REQUESTS_PER_MINUTE
    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {limit} requests/minute",
            headers={"Retry-After": "60"},
        )


# =============================================================================
# Pagination parameters
# =============================================================================

class PaginationParams:
    """Reusable pagination query parameters."""

    def __init__(
        self,
        skip: int = 0,
        limit: int = 50,
    ) -> None:
        self.skip = max(0, skip)
        self.limit = min(max(1, limit), 200)  # cap at 200 to prevent abuse


Pagination = Annotated[PaginationParams, Depends(PaginationParams)]