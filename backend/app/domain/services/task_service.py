# =============================================================================
# app/domain/services/task_service.py
# Task orchestration domain service.
# Handles: task creation, status polling, progress updates.
# Does NOT import Celery directly — that stays in infrastructure/.
# =============================================================================
from __future__ import annotations

from uuid import UUID

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.entities.task import TaskEntity
from app.domain.repositories.task_repository import ITaskRepository
from app.domain.repositories.video_repository import IVideoRepository
from app.model.models_task import TaskStatus, TaskType

logger = get_logger(__name__)


class TaskService:
    """Manages task lifecycle and progress tracking."""

    def __init__(
        self,
        task_repo: ITaskRepository,
        video_repo: IVideoRepository,
    ) -> None:
        self._task_repo = task_repo
        self._video_repo = video_repo

    async def create_task(
        self,
        video_id: UUID,
        task_type: TaskType,
    ) -> TaskEntity:
        """
        Create a new task record in PENDING state for a video.
        Returns the TaskEntity before the Celery task ID is assigned.

        Raises:
            NotFoundError: If the video doesn't exist.
        """
        video = await self._video_repo.get_by_id(video_id)
        if video is None:
            raise NotFoundError(resource="Video", identifier=str(video_id))

        task = await self._task_repo.create(
            {
                "video_id": video_id,
                "task_type": task_type,
                "status": TaskStatus.PENDING,
                "retry_count": 0,
                "progress": 0.0,
                "log": [],
            }
        )

        logger.info(
            "task.created",
            task_id=str(task.id),
            video_id=str(video_id),
            task_type=task_type,
        )
        return task

    async def bind_celery_id(
        self, task_id: UUID, celery_task_id: str
    ) -> None:
        """
        Store the Celery task ID in the DB after apply_async() returns.
        This links the DB record to the Celery broker entry.
        """
        await self._task_repo.set_celery_task_id(task_id, celery_task_id)
        logger.debug(
            "task.celery_id_bound",
            task_id=str(task_id),
            celery_task_id=celery_task_id,
        )

    async def get_task(self, task_id: UUID, *, owner_id: UUID) -> TaskEntity:
        """
        Retrieve a task, verifying the requester owns the associated video.

        Raises:
            NotFoundError: If the task doesn't exist or ownership mismatch.
        """
        task = await self._task_repo.get_by_id(task_id)
        if task is None:
            raise NotFoundError(resource="Task", identifier=str(task_id))

        video = await self._video_repo.get_by_id(task.video_id)
        if video is None or video.owner_id != owner_id:
            raise NotFoundError(resource="Task", identifier=str(task_id))

        return task

    async def list_tasks_for_video(
        self,
        video_id: UUID,
        *,
        owner_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> list[TaskEntity]:
        """
        List all tasks for a video, verifying ownership.

        Raises:
            NotFoundError: If video doesn't exist or ownership mismatch.
        """
        video = await self._video_repo.get_by_id(video_id)
        if video is None or video.owner_id != owner_id:
            raise NotFoundError(resource="Video", identifier=str(video_id))

        return await self._task_repo.get_by_video(video_id, skip=skip, limit=limit)

    async def get_latest_task(
        self,
        video_id: UUID,
        *,
        owner_id: UUID,
        task_type: str | None = None,
    ) -> TaskEntity | None:
        """Return the most recent task for a video, optionally filtered by type."""
        video = await self._video_repo.get_by_id(video_id)
        if video is None or video.owner_id != owner_id:
            raise NotFoundError(resource="Video", identifier=str(video_id))

        return await self._task_repo.get_latest_by_video(video_id, task_type)

    async def update_progress(
        self,
        task_id: UUID,
        *,
        progress: float,
        message: str | None = None,
    ) -> None:
        """Called by Celery workers to report incremental progress."""
        await self._task_repo.update_status(
            task_id,
            status=TaskStatus.STARTED,
            progress=progress,
            progress_message=message,
        )

    async def append_log(self, task_id: UUID, message: str) -> None:
        """Append a processing step log entry."""
        await self._task_repo.append_log(task_id, message)