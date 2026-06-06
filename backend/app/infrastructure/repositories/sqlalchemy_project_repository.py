# =============================================================================
# app/infrastructure/repositories/sqlalchemy_project_repository.py
# SQLAlchemy 2.0 implementation of IProjectRepository.
# =============================================================================
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsError
from app.domain.entities.project import ProjectEntity
from app.domain.repositories.project_repository import IProjectRepository
from app.model.models_project import Project


class SQLAlchemyProjectRepository(IProjectRepository):

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # AbstractRepository
    # ------------------------------------------------------------------

    async def get_by_id(self, entity_id: UUID) -> ProjectEntity | None:
        stmt = select(Project).where(
            Project.id == entity_id, Project.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        project = result.scalar_one_or_none()
        return self._to_entity(project) if project else None

    async def get_all(self, *, skip: int = 0, limit: int = 100) -> list[ProjectEntity]:
        stmt = (
            select(Project)
            .where(Project.deleted_at.is_(None))
            .order_by(Project.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(p) for p in result.scalars().all()]

    async def create(self, entity_data: dict) -> ProjectEntity:
        project = Project(**entity_data)
        self._session.add(project)
        try:
            await self._session.flush()
            await self._session.refresh(project)
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise AlreadyExistsError(resource="Project", field="slug") from exc
            raise
        return self._to_entity(project)

    async def update(self, entity_id: UUID, update_data: dict) -> ProjectEntity | None:
        stmt = (
            update(Project)
            .where(Project.id == entity_id, Project.deleted_at.is_(None))
            .values(**update_data)
            .returning(Project)
        )
        result = await self._session.execute(stmt)
        project = result.scalar_one_or_none()
        return self._to_entity(project) if project else None

    async def delete(self, entity_id: UUID) -> bool:
        stmt = (
            update(Project)
            .where(Project.id == entity_id)
            .values(deleted_at=datetime.now(UTC))
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def count(self) -> int:
        stmt = select(func.count(Project.id)).where(Project.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    # ------------------------------------------------------------------
    # SoftDeletableRepository
    # ------------------------------------------------------------------

    async def soft_delete(self, entity_id: UUID) -> bool:
        stmt = (
            update(Project)
            .where(Project.id == entity_id, Project.deleted_at.is_(None))
            .values(deleted_at=datetime.now(UTC))
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def restore(self, entity_id: UUID) -> ProjectEntity | None:
        stmt = (
            update(Project)
            .where(Project.id == entity_id, Project.deleted_at.isnot(None))
            .values(deleted_at=None)
            .returning(Project)
        )
        result = await self._session.execute(stmt)
        p = result.scalar_one_or_none()
        return self._to_entity(p) if p else None

    async def get_deleted(self, *, skip: int = 0, limit: int = 100) -> list[ProjectEntity]:
        stmt = (
            select(Project)
            .where(Project.deleted_at.isnot(None))
            .order_by(Project.deleted_at.desc())
            .offset(skip).limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(p) for p in result.scalars().all()]

    # ------------------------------------------------------------------
    # IProjectRepository
    # ------------------------------------------------------------------

    async def get_by_owner(
        self, owner_id: UUID, *, skip: int = 0, limit: int = 100
    ) -> list[ProjectEntity]:
        stmt = (
            select(Project)
            .where(Project.owner_id == owner_id, Project.deleted_at.is_(None))
            .order_by(Project.created_at.desc())
            .offset(skip).limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(p) for p in result.scalars().all()]

    async def get_by_slug(self, owner_id: UUID, slug: str) -> ProjectEntity | None:
        stmt = select(Project).where(
            Project.owner_id == owner_id,
            Project.slug == slug,
            Project.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        p = result.scalar_one_or_none()
        return self._to_entity(p) if p else None

    async def slug_exists(self, owner_id: UUID, slug: str) -> bool:
        stmt = select(func.count(Project.id)).where(
            Project.owner_id == owner_id,
            Project.slug == slug,
            Project.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return (result.scalar_one() or 0) > 0

    async def count_by_owner(self, owner_id: UUID) -> int:
        stmt = select(func.count(Project.id)).where(
            Project.owner_id == owner_id,
            Project.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def increment_video_count(self, project_id: UUID) -> bool:
        stmt = (
            update(Project)
            .where(Project.id == project_id)
            .values(video_count=Project.video_count + 1)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def decrement_video_count(self, project_id: UUID) -> bool:
        stmt = (
            update(Project)
            .where(Project.id == project_id, Project.video_count > 0)
            .values(video_count=Project.video_count - 1)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def get_by_id_and_owner(
        self, project_id: UUID, owner_id: UUID
    ) -> ProjectEntity | None:
        stmt = select(Project).where(
            Project.id == project_id,
            Project.owner_id == owner_id,
            Project.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        p = result.scalar_one_or_none()
        return self._to_entity(p) if p else None

    # ------------------------------------------------------------------
    # Mapper
    # ------------------------------------------------------------------

    @staticmethod
    def _to_entity(p: Project) -> ProjectEntity:
        return ProjectEntity(
            id=p.id,
            name=p.name,
            slug=p.slug,
            description=p.description,
            owner_id=p.owner_id,
            default_voice_model=p.default_voice_model,
            default_language=p.default_language,
            default_llm_model=p.default_llm_model,
            video_count=p.video_count,
            created_at=p.created_at,
            updated_at=p.updated_at,
            deleted_at=p.deleted_at,
        )