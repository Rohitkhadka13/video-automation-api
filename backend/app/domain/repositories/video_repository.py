# =============================================================================
# app/domain/repositories/video_repository.py
# Abstract interface for video persistence operations.
# =============================================================================
from __future__ import annotations

from abc import abstractmethod
from uuid import UUID

from app.domain.entities.video import VideoEntity
from app.domain.repositories.base import SoftDeletableRepository


class IVideoRepository(SoftDeletableRepository[VideoEntity]):
    """Domain contract for video persistence."""

    @abstractmethod
    async def get_by_project(
        self,
        project_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
        status_filter: list[str] | None = None,
    ) -> list[VideoEntity]:
        """
        Return paginated videos belonging to a project.

        Args:
            project_id:    Filter by project.
            skip/limit:    Pagination.
            status_filter: If provided, only return videos with these statuses.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_owner(
        self,
        owner_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[VideoEntity]:
        """Return all videos owned by a user across all their projects."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_project_and_owner(
        self,
        project_id: UUID,
        owner_id: UUID,
        video_id: UUID,
    ) -> VideoEntity | None:
        """
        Retrieve a video only if it belongs to the project AND is owned by owner_id.
        Single-query authorization + fetch — avoids N+1 auth checks.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_slug(
        self, project_id: UUID, slug: str
    ) -> VideoEntity | None:
        """Retrieve a video by project + slug (the composite unique key)."""
        raise NotImplementedError

    @abstractmethod
    async def update_status(
        self,
        video_id: UUID,
        status: str,
        *,
        error_message: str | None = None,
    ) -> bool:
        """
        Atomically update a video's status column.
        This is the hot path called by Celery workers — must be fast.

        Returns:
            True on success, False if video_id not found.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_storage_key(
        self,
        video_id: UUID,
        *,
        storage_key: str,
        mime_type: str,
        file_size_bytes: int,
    ) -> bool:
        """Update storage key and file metadata after upload completes."""
        raise NotImplementedError

    @abstractmethod
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
        """Update output file metadata after FFmpeg processing."""
        raise NotImplementedError

    @abstractmethod
    async def update_processing_metadata(
        self, video_id: UUID, metadata: dict
    ) -> bool:
        """
        Merge new key-value pairs into the processing_metadata JSONB column.
        Uses PostgreSQL's jsonb_set / || operator for atomic partial update.
        """
        raise NotImplementedError

    @abstractmethod
    async def count_by_project(
        self,
        project_id: UUID,
        *,
        status_filter: list[str] | None = None,
    ) -> int:
        """Return video count for a project, optionally filtered by status."""
        raise NotImplementedError

    @abstractmethod
    async def get_stale_processing(
        self, older_than_minutes: int = 60
    ) -> list[VideoEntity]:
        """
        Return videos stuck in PROCESSING status for longer than the threshold.
        Used by a scheduled Celery beat task to detect and recover stuck jobs.
        """
        raise NotImplementedError