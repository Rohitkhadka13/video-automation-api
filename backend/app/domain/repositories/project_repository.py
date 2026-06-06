# =============================================================================
# app/domain/repositories/project_repository.py
# Abstract interface for project persistence operations.
# =============================================================================
from __future__ import annotations

from abc import abstractmethod
from uuid import UUID

from app.domain.entities.project import ProjectEntity
from app.domain.repositories.base import SoftDeletableRepository


class IProjectRepository(SoftDeletableRepository[ProjectEntity]):
    """Domain contract for project persistence."""

    @abstractmethod
    async def get_by_owner(
        self,
        owner_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ProjectEntity]:
        """
        Return paginated projects owned by a specific user.
        Excludes soft-deleted projects.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_slug(
        self, owner_id: UUID, slug: str
    ) -> ProjectEntity | None:
        """
        Retrieve a project by owner + slug (the unique composite key).

        Returns:
            ProjectEntity if found, None if not found or soft-deleted.
        """
        raise NotImplementedError

    @abstractmethod
    async def slug_exists(self, owner_id: UUID, slug: str) -> bool:
        """
        Check if a slug already exists for this owner.
        Used before creating a project to detect duplicates.
        """
        raise NotImplementedError

    @abstractmethod
    async def count_by_owner(self, owner_id: UUID) -> int:
        """Return total non-deleted project count for an owner."""
        raise NotImplementedError

    @abstractmethod
    async def increment_video_count(self, project_id: UUID) -> bool:
        """
        Atomically increment video_count by 1.
        Called when a new video is added to a project.

        Returns:
            True on success, False if project_id not found.
        """
        raise NotImplementedError

    @abstractmethod
    async def decrement_video_count(self, project_id: UUID) -> bool:
        """
        Atomically decrement video_count by 1 (floor at 0).
        Called when a video is deleted from a project.

        Returns:
            True on success, False if project_id not found.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_id_and_owner(
        self, project_id: UUID, owner_id: UUID
    ) -> ProjectEntity | None:
        """
        Retrieve a project only if it belongs to the given owner.
        Combines authorization check with data fetch in one query.

        Returns:
            ProjectEntity if found and owned by owner_id, None otherwise.
        """
        raise NotImplementedError