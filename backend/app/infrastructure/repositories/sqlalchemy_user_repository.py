# =============================================================================
# app/infrastructure/repositories/sqlalchemy_user_repository.py
# SQLAlchemy 2.0 implementation of IUserRepository.
#
# Mapper pattern: all methods convert ORM models → domain entities before
# returning. The domain layer never sees a SQLAlchemy model object.
# =============================================================================
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsError
from app.core.logging import get_logger
from app.domain.entities.user import UserEntity
from app.domain.repositories.user_repository import IUserRepository
from app.model.models_user import User

logger = get_logger(__name__)


class SQLAlchemyUserRepository(IUserRepository):
    """Concrete user repository backed by PostgreSQL via asyncpg."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # AbstractRepository interface
    # ------------------------------------------------------------------

    async def get_by_id(self, entity_id: UUID) -> UserEntity | None:
        stmt = (
            select(User)
            .where(User.id == entity_id, User.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        return self._to_entity(user) if user else None

    async def get_all(self, *, skip: int = 0, limit: int = 100) -> list[UserEntity]:
        stmt = (
            select(User)
            .where(User.deleted_at.is_(None))
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(u) for u in result.scalars().all()]

    async def create(self, entity_data: dict) -> UserEntity:
        user = User(**entity_data)
        self._session.add(user)
        try:
            await self._session.flush()  # assigns DB-generated id/timestamps
            await self._session.refresh(user)
        except Exception as exc:
            if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
                raise AlreadyExistsError(resource="User", field="email") from exc
            raise
        return self._to_entity(user)

    async def update(self, entity_id: UUID, update_data: dict) -> UserEntity | None:
        stmt = (
            update(User)
            .where(User.id == entity_id, User.deleted_at.is_(None))
            .values(**update_data)
            .returning(User)
        )
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        return self._to_entity(user) if user else None

    async def delete(self, entity_id: UUID) -> bool:
        stmt = (
            update(User)
            .where(User.id == entity_id)
            .values(deleted_at=datetime.now(UTC))
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def count(self) -> int:
        stmt = select(func.count(User.id)).where(User.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one()

    # ------------------------------------------------------------------
    # SoftDeletableRepository interface
    # ------------------------------------------------------------------

    async def soft_delete(self, entity_id: UUID) -> bool:
        stmt = (
            update(User)
            .where(User.id == entity_id, User.deleted_at.is_(None))
            .values(deleted_at=datetime.now(UTC))
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def restore(self, entity_id: UUID) -> UserEntity | None:
        stmt = (
            update(User)
            .where(User.id == entity_id, User.deleted_at.isnot(None))
            .values(deleted_at=None)
            .returning(User)
        )
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        return self._to_entity(user) if user else None

    async def get_deleted(self, *, skip: int = 0, limit: int = 100) -> list[UserEntity]:
        stmt = (
            select(User)
            .where(User.deleted_at.isnot(None))
            .order_by(User.deleted_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(u) for u in result.scalars().all()]

    # ------------------------------------------------------------------
    # IUserRepository domain-specific methods
    # ------------------------------------------------------------------

    async def get_by_email(self, email: str) -> UserEntity | None:
        stmt = select(User).where(
            func.lower(User.email) == email.lower(),
            User.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        return self._to_entity(user) if user else None

    async def get_by_email_include_inactive(self, email: str) -> UserEntity | None:
        stmt = select(User).where(
            func.lower(User.email) == email.lower(),
            User.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        return self._to_entity(user) if user else None

    async def get_active_by_id(self, user_id: UUID) -> UserEntity | None:
        stmt = select(User).where(
            User.id == user_id,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        return self._to_entity(user) if user else None

    async def email_exists(self, email: str) -> bool:
        stmt = select(func.count(User.id)).where(
            func.lower(User.email) == email.lower(),
            User.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return (result.scalar_one() or 0) > 0

    async def update_password(self, user_id: UUID, hashed_password: str) -> bool:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(hashed_password=hashed_password)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def update_refresh_token_family(self, user_id: UUID, new_family: str) -> bool:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(refresh_token_family=new_family)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def set_active(self, user_id: UUID, is_active: bool) -> bool:
        stmt = (
            update(User)
            .where(User.id == user_id, User.deleted_at.is_(None))
            .values(is_active=is_active)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def set_verified(self, user_id: UUID, is_verified: bool) -> bool:
        stmt = (
            update(User)
            .where(User.id == user_id, User.deleted_at.is_(None))
            .values(is_verified=is_verified)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def get_by_role(
        self, role: str, *, skip: int = 0, limit: int = 100
    ) -> list[UserEntity]:
        stmt = (
            select(User)
            .where(User.role == role, User.deleted_at.is_(None))
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(u) for u in result.scalars().all()]

    async def count_active(self) -> int:
        stmt = select(func.count(User.id)).where(
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    # ------------------------------------------------------------------
    # ORM → entity mapper
    # ------------------------------------------------------------------

    @staticmethod
    def _to_entity(user: User) -> UserEntity:
        """Convert a SQLAlchemy User model to an immutable UserEntity."""
        return UserEntity(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            hashed_password=user.hashed_password,
            is_active=user.is_active,
            is_verified=user.is_verified,
            role=user.role,
            refresh_token_family=user.refresh_token_family,
            avatar_url=user.avatar_url,
            bio=user.bio,
            created_at=user.created_at,
            updated_at=user.updated_at,
            deleted_at=user.deleted_at,
        )