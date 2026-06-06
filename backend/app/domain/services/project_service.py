# =============================================================================
# app/domain/services/project_service.py
# Project management domain service.
# =============================================================================
from __future__ import annotations

from uuid import UUID

from slugify import slugify
from app.core.exceptions import AlreadyExistsError, NotFoundError, InsufficientPermissionsError
from app.core.logging import get_logger
from app.domain.entities.project import ProjectEntity
from app.domain.repositories.project_repository import IProjectRepository

logger = get_logger(__name__)


class ProjectService:
    """Handles project CRUD and ownership enforcement."""

    def __init__(self, project_repo: IProjectRepository) -> None:
        self._project_repo = project_repo

    async def create_project(
        self,
        *,
        owner_id: UUID,
        name: str,
        description: str | None = None,
        default_voice_model: str = "en_US-lessac-medium",
        default_language: str = "en",
        default_llm_model: str = "llama3",
    ) -> ProjectEntity:
        """
        Create a new project for an owner.

        Raises:
            AlreadyExistsError: If the generated slug already exists for this owner.
        """
        base_slug = slugify(name, max_length=250)
        slug = await self._unique_slug(owner_id, base_slug)

        project = await self._project_repo.create(
            {
                "owner_id": owner_id,
                "name": name.strip(),
                "slug": slug,
                "description": description,
                "default_voice_model": default_voice_model,
                "default_language": default_language,
                "default_llm_model": default_llm_model,
                "video_count": 0,
            }
        )

        logger.info("project.created", project_id=str(project.id), owner_id=str(owner_id))
        return project

    async def get_project(self, project_id: UUID, *, owner_id: UUID) -> ProjectEntity:
        """
        Retrieve a project, enforcing ownership.

        Raises:
            NotFoundError: If the project doesn't exist or isn't owned by owner_id.
        """
        project = await self._project_repo.get_by_id_and_owner(project_id, owner_id)
        if project is None:
            raise NotFoundError(resource="Project", identifier=str(project_id))
        return project

    async def list_projects(
        self,
        owner_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ProjectEntity]:
        """Return paginated projects for an owner."""
        return await self._project_repo.get_by_owner(owner_id, skip=skip, limit=limit)

    async def update_project(
        self,
        project_id: UUID,
        *,
        owner_id: UUID,
        name: str | None = None,
        description: str | None = None,
        default_voice_model: str | None = None,
        default_language: str | None = None,
        default_llm_model: str | None = None,
    ) -> ProjectEntity:
        """
        Update project fields. Only provided fields are changed.

        Raises:
            NotFoundError: If the project doesn't exist or isn't owned by owner_id.
            AlreadyExistsError: If the new name produces a slug that already exists.
        """
        # Verify ownership first
        await self.get_project(project_id, owner_id=owner_id)

        update_data: dict = {}
        if name is not None:
            new_slug = slugify(name, max_length=250)
            # Only regenerate slug if name actually changed
            unique_slug = await self._unique_slug(owner_id, new_slug, exclude_id=project_id)
            update_data["name"] = name.strip()
            update_data["slug"] = unique_slug
        if description is not None:
            update_data["description"] = description or None
        if default_voice_model is not None:
            update_data["default_voice_model"] = default_voice_model
        if default_language is not None:
            update_data["default_language"] = default_language
        if default_llm_model is not None:
            update_data["default_llm_model"] = default_llm_model

        if not update_data:
            return await self.get_project(project_id, owner_id=owner_id)

        project = await self._project_repo.update(project_id, update_data)
        if project is None:
            raise NotFoundError(resource="Project", identifier=str(project_id))

        logger.info("project.updated", project_id=str(project_id), fields=list(update_data.keys()))
        return project

    async def delete_project(self, project_id: UUID, *, owner_id: UUID) -> None:
        """
        Soft-delete a project and all its videos (cascade via DB FK).

        Raises:
            NotFoundError: If the project doesn't exist or isn't owned by owner_id.
        """
        await self.get_project(project_id, owner_id=owner_id)
        await self._project_repo.soft_delete(project_id)
        logger.info("project.deleted", project_id=str(project_id), owner_id=str(owner_id))

    async def count_projects(self, owner_id: UUID) -> int:
        """Return total project count for an owner."""
        return await self._project_repo.count_by_owner(owner_id)

    async def _unique_slug(
        self, owner_id: UUID, base_slug: str, exclude_id: UUID | None = None
    ) -> str:
        """
        Generate a slug that is unique within this owner's projects.
        Appends -2, -3, etc. until unique.
        """
        slug = base_slug
        counter = 1
        while True:
            exists = await self._project_repo.slug_exists(owner_id, slug)
            if not exists:
                return slug
            # If the slug belongs to the project being updated, it's fine
            if exclude_id is not None:
                existing = await self._project_repo.get_by_slug(owner_id, slug)
                if existing is not None and existing.id == exclude_id:
                    return slug
            counter += 1
            slug = f"{base_slug}-{counter}"