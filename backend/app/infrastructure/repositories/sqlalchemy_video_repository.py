# =============================================================================
# app/infrastructure/repositories/sqlalchemy_video_repository.py
# SQLAlchemy 2.0 implementation of IVideoRepository.
# =============================================================================
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.video import VideoEntity
from app.domain.repositories.video_repository import IVideoRepository
from app.model.models_video import Video


class SQLAlchemyVideoRepository(IVideoRepository):

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # AbstractRepository
    # ------------------------------------------------------------------

    async def get_by_id(self, entity_id: UUID) -> VideoEntity | None:
        stmt = select(Video).where(
            Video.id == entity_id, Video.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        v = result.scalar_one_or_none()
        return self._to_entity(v) if v else None

    async def get_all(self, *, skip: int = 0, limit: int = 100) -> list[VideoEntity]:
        stmt = (
            select(Video)
            .where(Video.deleted_at.is_(None))
            .order_by(Video.created_at.desc())
            .offset(skip).limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(v) for v in result.scalars().all()]

    async def create(self, entity_data: dict) -> VideoEntity:
        video = Video(**entity_data)
        self._session.add(video)
        await self._session.flush()
        await self._session.refresh(video)
        return self._to_entity(video)

    async def update(self, entity_id: UUID, update_data: dict) -> VideoEntity | None:
        stmt = (
            update(Video)
            .where(Video.id == entity_id, Video.deleted_at.is_(None))
            .values(**update_data)
            .returning(Video)
        )
        result = await self._session.execute(stmt)
        v = result.scalar_one_or_none()
        return self._to_entity(v) if v else None

    async def delete(self, entity_id: UUID) -> bool:
        stmt = (
            update(Video)
            .where(Video.id == entity_id)
            .values(deleted_at=datetime.now(UTC))
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def count(self) -> int:
        stmt = select(func.count(Video.id)).where(Video.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    # ------------------------------------------------------------------
    # SoftDeletableRepository
    # ------------------------------------------------------------------

    async def soft_delete(self, entity_id: UUID) -> bool:
        stmt = (
            update(Video)
            .where(Video.id == entity_id, Video.deleted_at.is_(None))
            .values(deleted_at=datetime.now(UTC))
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def restore(self, entity_id: UUID) -> VideoEntity | None:
        stmt = (
            update(Video)
            .where(Video.id == entity_id, Video.deleted_at.isnot(None))
            .values(deleted_at=None)
            .returning(Video)
        )
        result = await self._session.execute(stmt)
        v = result.scalar_one_or_none()
        return self._to_entity(v) if v else None

    async def get_deleted(self, *, skip: int = 0, limit: int = 100) -> list[VideoEntity]:
        stmt = (
            select(Video)
            .where(Video.deleted_at.isnot(None))
            .order_by(Video.deleted_at.desc())
            .offset(skip).limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(v) for v in result.scalars().all()]

    # ------------------------------------------------------------------
    # IVideoRepository
    # ------------------------------------------------------------------

    async def get_by_project(
        self,
        project_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
        status_filter: list[str] | None = None,
    ) -> list[VideoEntity]:
        stmt = select(Video).where(
            Video.project_id == project_id,
            Video.deleted_at.is_(None),
        )
        if status_filter:
            stmt = stmt.where(Video.status.in_(status_filter))
        stmt = stmt.order_by(Video.created_at.desc()).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_entity(v) for v in result.scalars().all()]

    async def get_by_owner(
        self, owner_id: UUID, *, skip: int = 0, limit: int = 100
    ) -> list[VideoEntity]:
        stmt = (
            select(Video)
            .where(Video.owner_id == owner_id, Video.deleted_at.is_(None))
            .order_by(Video.created_at.desc())
            .offset(skip).limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(v) for v in result.scalars().all()]

    async def get_by_project_and_owner(
        self, project_id: UUID, owner_id: UUID, video_id: UUID
    ) -> VideoEntity | None:
        stmt = select(Video).where(
            Video.id == video_id,
            Video.project_id == project_id,
            Video.owner_id == owner_id,
            Video.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        v = result.scalar_one_or_none()
        return self._to_entity(v) if v else None

    async def get_by_slug(self, project_id: UUID, slug: str) -> VideoEntity | None:
        stmt = select(Video).where(
            Video.project_id == project_id,
            Video.slug == slug,
            Video.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        v = result.scalar_one_or_none()
        return self._to_entity(v) if v else None

    async def update_status(
        self,
        video_id: UUID,
        status: str,
        *,
        error_message: str | None = None,
    ) -> bool:
        values: dict = {"status": status}
        if error_message is not None:
            values["error_message"] = error_message
        stmt = (
            update(Video)
            .where(Video.id == video_id)
            .values(**values)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def update_storage_key(
        self,
        video_id: UUID,
        *,
        storage_key: str,
        mime_type: str,
        file_size_bytes: int,
    ) -> bool:
        stmt = (
            update(Video)
            .where(Video.id == video_id)
            .values(
                storage_key=storage_key,
                mime_type=mime_type,
                file_size_bytes=file_size_bytes,
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def update_output(
        self,
        video_id: UUID,
        *,
        output_storage_key: str,
        thumbnail_storage_key: str | None,
        duration_seconds: float | None,
        width: int | None,
        height: int | None,
        fps: float | None,
    ) -> bool:
        stmt = (
            update(Video)
            .where(Video.id == video_id)
            .values(
                output_storage_key=output_storage_key,
                thumbnail_storage_key=thumbnail_storage_key,
                duration_seconds=duration_seconds,
                width=width,
                height=height,
                fps=fps,
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def update_processing_metadata(
        self, video_id: UUID, metadata: dict
    ) -> bool:
        # PostgreSQL JSONB merge: existing || new (new values overwrite on key conflict)
        from sqlalchemy import text
        stmt = text(
            "UPDATE videos SET processing_metadata = "
            "COALESCE(processing_metadata, '{}'::jsonb) || :meta::jsonb "
            "WHERE id = :vid_id"
        )
        result = await self._session.execute(
            stmt,
            {"meta": __import__("json").dumps(metadata), "vid_id": str(video_id)},
        )
        return result.rowcount > 0

    async def count_by_project(
        self,
        project_id: UUID,
        *,
        status_filter: list[str] | None = None,
    ) -> int:
        stmt = select(func.count(Video.id)).where(
            Video.project_id == project_id,
            Video.deleted_at.is_(None),
        )
        if status_filter:
            stmt = stmt.where(Video.status.in_(status_filter))
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def get_stale_processing(
        self, older_than_minutes: int = 60
    ) -> list[VideoEntity]:
        cutoff = datetime.now(UTC) - timedelta(minutes=older_than_minutes)
        stmt = select(Video).where(
            Video.status == "processing",
            Video.updated_at < cutoff,
            Video.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(v) for v in result.scalars().all()]

    # ------------------------------------------------------------------
    # Mapper
    # ------------------------------------------------------------------

    @staticmethod
    def _to_entity(v: Video) -> VideoEntity:
        return VideoEntity(
            id=v.id,
            title=v.title,
            slug=v.slug,
            description=v.description,
            project_id=v.project_id,
            owner_id=v.owner_id,
            status=v.status,
            error_message=v.error_message,
            original_filename=v.original_filename,
            storage_key=v.storage_key,
            mime_type=v.mime_type,
            file_size_bytes=v.file_size_bytes,
            output_storage_key=v.output_storage_key,
            thumbnail_storage_key=v.thumbnail_storage_key,
            duration_seconds=v.duration_seconds,
            width=v.width,
            height=v.height,
            fps=v.fps,
            voice_model=v.voice_model,
            language=v.language,
            script_prompt=v.script_prompt,
            processing_metadata=v.processing_metadata,
            created_at=v.created_at,
            updated_at=v.updated_at,
            deleted_at=v.deleted_at,
        )