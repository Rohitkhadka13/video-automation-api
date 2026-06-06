# =============================================================================
# app/domain/repositories/task_repository.py
# Abstract interface for task persistence operations.
# =============================================================================
from __future__ import annotations

from abc import abstractmethod
from uuid import UUID

from app.domain.entities.task import TaskEntity
from app.domain.repositories.base import AbstractRepository


class ITaskRepository(AbstractRepository[TaskEntity]):
    """
    Domain contract for VideoTask persistence.

    Tasks are append-only records — they are never soft-deleted.
    A new task record is created for each retry attempt.
    """

    @abstractmethod
    async def get_by_video(
        self,
        video_id: UUID,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[TaskEntity]:
        """
        Return all task records for a video, newest first.
        Includes all task types (transcription, TTS, processing, etc.).
        """
        raise NotImplementedError

    @abstractmethod
    async def get_latest_by_video(
        self, video_id: UUID, task_type: str | None = None
    ) -> TaskEntity | None:
        """
        Return the most recent task record for a video.

        Args:
            video_id:  Target video.
            task_type: If provided, filter to this task type only.

        Returns:
            Most recent TaskEntity, or None if no tasks exist.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_celery_id(self, celery_task_id: str) -> TaskEntity | None:
        """
        Retrieve a task by its Celery task ID.
        Called from Celery signal handlers to update task state.
        """
        raise NotImplementedError

    @abstractmethod
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
        """
        Update task status and optional progress/error fields atomically.
        Called frequently by Celery workers — must be efficient.

        Returns:
            True on success, False if task_id not found.
        """
        raise NotImplementedError

    @abstractmethod
    async def set_celery_task_id(
        self, task_id: UUID, celery_task_id: str
    ) -> bool:
        """
        Store the Celery task ID after the task has been dispatched.
        Called immediately after celery_task.apply_async().

        Returns:
            True on success, False if task_id not found.
        """
        raise NotImplementedError

    @abstractmethod
    async def append_log(self, task_id: UUID, message: str) -> bool:
        """
        Atomically append a log entry to the task's log JSONB array.
        Uses PostgreSQL's jsonb_set for safe concurrent appends.

        Returns:
            True on success, False if task_id not found.
        """
        raise NotImplementedError

    @abstractmethod
    async def mark_started(self, task_id: UUID) -> bool:
        """Set status=STARTED and started_at=now(). Returns True on success."""
        raise NotImplementedError

    @abstractmethod
    async def mark_success(
        self, task_id: UUID, result_data: dict | None = None
    ) -> bool:
        """Set status=SUCCESS, progress=1.0, completed_at=now(), store result."""
        raise NotImplementedError

    @abstractmethod
    async def mark_failure(
        self,
        task_id: UUID,
        *,
        error_type: str,
        error_message: str,
        traceback: str | None = None,
    ) -> bool:
        """Set status=FAILURE, completed_at=now(), store error details."""
        raise NotImplementedError

    @abstractmethod
    async def count_by_video(self, video_id: UUID) -> int:
        """Return total task count for a video (including retries)."""
        raise NotImplementedError