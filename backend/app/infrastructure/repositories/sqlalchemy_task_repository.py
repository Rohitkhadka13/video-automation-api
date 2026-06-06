# =============================================================================
# app/infrastructure/repositories/sqlalchemy_task_repository.py
# SQLAlchemy 2.0 implementation of ITaskRepository.
# =============================================================================
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.task import TaskEntity
from app.domain.repositories.task_repository import ITaskRepository
from app.model.models_task import TaskStatus, VideoTask


class SQLAlchemyTaskRepository(ITaskRepository):

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # AbstractRepository
    # ------------------------------------------------------------------

    async def get_by_id(self, entity_id: UUID) -> TaskEntity | None:
        stmt = select(VideoTask).where(VideoTask.id == entity_id)
        result = await self._session.execute(stmt)
        t = result.scalar_one_or_none()
        return self._to_entity(t) if t else None

    async def get_all(self, *, skip: int = 0, limit: int = 100) -> list[TaskEntity]:
        stmt = (
            select(VideoTask)
            .order_by(VideoTask.created_at.desc())
            .offset(skip).limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(t) for t in result.scalars().all()]

    async def create(self, entity_data: dict) -> TaskEntity:
        task = VideoTask(**entity_data)
        self._session.add(task)
        await self._session.flush()
        await self._session.refresh(task)
        return self._to_entity(task)

    async def update(self, entity_id: UUID, update_data: dict) -> TaskEntity | None:
        stmt = (
            update(VideoTask)
            .where(VideoTask.id == entity_id)
            .values(**update_data)
            .returning(VideoTask)
        )
        result = await self._session.execute(stmt)
        t = result.scalar_one_or_none()
        return self._to_entity(t) if t else None

    async def delete(self, entity_id: UUID) -> bool:
        stmt = (
            update(VideoTask)
            .where(VideoTask.id == entity_id)
            .values(status=TaskStatus.REVOKED)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def count(self) -> int:
        stmt = select(func.count(VideoTask.id))
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    # ------------------------------------------------------------------
    # ITaskRepository
    # ------------------------------------------------------------------

    async def get_by_video(
        self, video_id: UUID, *, skip: int = 0, limit: int = 20
    ) -> list[TaskEntity]:
        stmt = (
            select(VideoTask)
            .where(VideoTask.video_id == video_id)
            .order_by(VideoTask.created_at.desc())
            .offset(skip).limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(t) for t in result.scalars().all()]

    async def get_latest_by_video(
        self, video_id: UUID, task_type: str | None = None
    ) -> TaskEntity | None:
        stmt = select(VideoTask).where(VideoTask.video_id == video_id)
        if task_type:
            stmt = stmt.where(VideoTask.task_type == task_type)
        stmt = stmt.order_by(VideoTask.created_at.desc()).limit(1)
        result = await self._session.execute(stmt)
        t = result.scalar_one_or_none()
        return self._to_entity(t) if t else None

    async def get_by_celery_id(self, celery_task_id: str) -> TaskEntity | None:
        stmt = select(VideoTask).where(
            VideoTask.celery_task_id == celery_task_id
        )
        result = await self._session.execute(stmt)
        t = result.scalar_one_or_none()
        return self._to_entity(t) if t else None

    async def update_status(
        self,
        task_id: UUID,
        status: str,
        *,
        progress: float | None = None,
        progress_message: str | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        error_traceback: str | None = None,
    ) -> bool:
        values: dict = {"status": status}
        if progress is not None:
            values["progress"] = max(0.0, min(1.0, progress))
        if progress_message is not None:
            values["progress_message"] = progress_message
        if error_type is not None:
            values["error_type"] = error_type
        if error_message is not None:
            values["error_message"] = error_message
        if error_traceback is not None:
            values["error_traceback"] = error_traceback
        stmt = update(VideoTask).where(VideoTask.id == task_id).values(**values)
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def set_celery_task_id(self, task_id: UUID, celery_task_id: str) -> bool:
        stmt = (
            update(VideoTask)
            .where(VideoTask.id == task_id)
            .values(celery_task_id=celery_task_id)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def append_log(self, task_id: UUID, message: str) -> bool:
        """Atomically append to the JSONB log array using PostgreSQL || operator."""
        import json
        entry = f"{datetime.now(UTC).isoformat()} — {message}"
        stmt = text(
            "UPDATE video_tasks SET log = "
            "COALESCE(log, '[]'::jsonb) || :entry::jsonb "
            "WHERE id = :task_id"
        )
        result = await self._session.execute(
            stmt,
            {"entry": json.dumps([entry]), "task_id": str(task_id)},
        )
        return result.rowcount > 0

    async def mark_started(self, task_id: UUID) -> bool:
        stmt = (
            update(VideoTask)
            .where(VideoTask.id == task_id)
            .values(status=TaskStatus.STARTED, started_at=datetime.now(UTC))
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def mark_success(
        self, task_id: UUID, result_data: dict | None = None
    ) -> bool:
        now = datetime.now(UTC)
        values: dict = {
            "status": TaskStatus.SUCCESS,
            "completed_at": now,
            "progress": 1.0,
        }
        if result_data is not None:
            values["result_data"] = result_data
        # Calculate duration using a subquery for started_at
        stmt = text(
            "UPDATE video_tasks SET "
            "status = :status, completed_at = :completed_at, progress = 1.0, "
            "result_data = COALESCE(:result_data::jsonb, result_data), "
            "duration_seconds = EXTRACT(EPOCH FROM (:completed_at - started_at)) "
            "WHERE id = :task_id"
        )
        import json
        result = await self._session.execute(
            stmt,
            {
                "status": TaskStatus.SUCCESS,
                "completed_at": now,
                "result_data": json.dumps(result_data) if result_data else None,
                "task_id": str(task_id),
            },
        )
        return result.rowcount > 0

    async def mark_failure(
        self,
        task_id: UUID,
        *,
        error_type: str,
        error_message: str,
        traceback: str | None = None,
    ) -> bool:
        now = datetime.now(UTC)
        stmt = text(
            "UPDATE video_tasks SET "
            "status = :status, completed_at = :completed_at, "
            "error_type = :error_type, error_message = :error_message, "
            "error_traceback = :error_traceback, "
            "duration_seconds = EXTRACT(EPOCH FROM (:completed_at - started_at)) "
            "WHERE id = :task_id"
        )
        result = await self._session.execute(
            stmt,
            {
                "status": TaskStatus.FAILURE,
                "completed_at": now,
                "error_type": error_type,
                "error_message": error_message,
                "error_traceback": traceback,
                "task_id": str(task_id),
            },
        )
        return result.rowcount > 0

    async def count_by_video(self, video_id: UUID) -> int:
        stmt = select(func.count(VideoTask.id)).where(
            VideoTask.video_id == video_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    # ------------------------------------------------------------------
    # Mapper
    # ------------------------------------------------------------------

    @staticmethod
    def _to_entity(t: VideoTask) -> TaskEntity:
        return TaskEntity(
            id=t.id,
            video_id=t.video_id,
            celery_task_id=t.celery_task_id,
            task_type=t.task_type,
            status=t.status,
            retry_count=t.retry_count,
            progress=t.progress,
            progress_message=t.progress_message,
            result_data=t.result_data,
            error_type=t.error_type,
            error_message=t.error_message,
            error_traceback=t.error_traceback,
            log=t.log,
            started_at=t.started_at,
            completed_at=t.completed_at,
            duration_seconds=t.duration_seconds,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )