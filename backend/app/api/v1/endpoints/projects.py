# =============================================================================
# app/api/v1/endpoints/projects.py
# Project CRUD endpoints.
# =============================================================================
from __future__ import annotations

from typing import Annotated
from uuid import UUID


from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, Pagination, get_project_service
from app.core.exceptions import AlreadyExistsError, NotFoundError
from app.domain.services.project_service import ProjectService
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter()

ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]


def _to_read(p: object) -> ProjectRead:  # type: ignore[misc]
    return ProjectRead(
        id=p.id, name=p.name, slug=p.slug, description=p.description,
        owner_id=p.owner_id, default_voice_model=p.default_voice_model,
        default_language=p.default_language, default_llm_model=p.default_llm_model,
        video_count=p.video_count, created_at=p.created_at, updated_at=p.updated_at,
    )


@router.post(
    "/",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
)
async def create_project(
    body: ProjectCreate,
    current_user: CurrentUser,
    project_service: ProjectServiceDep,
) -> ProjectRead:
    """Create a new project owned by the current user."""
    project = await project_service.create_project(
        owner_id=current_user.id,
        name=body.name,
        description=body.description,
        default_voice_model=body.default_voice_model,
        default_language=body.default_language,
        default_llm_model=body.default_llm_model,
    )
    return _to_read(project)


@router.get(
    "/",
    response_model=PaginatedResponse[ProjectRead],
    summary="List all projects for the current user",
)
async def list_projects(
    current_user: CurrentUser,
    project_service: ProjectServiceDep,
    pagination: Pagination,
) -> PaginatedResponse[ProjectRead]:
    """Return paginated list of projects owned by the current user."""
    projects = await project_service.list_projects(
        current_user.id, skip=pagination.skip, limit=pagination.limit
    )
    total = await project_service.count_projects(current_user.id)
    return PaginatedResponse(
        items=[_to_read(p) for p in projects],
        total=total, skip=pagination.skip, limit=pagination.limit,
    )


@router.get(
    "/{project_id}",
    response_model=ProjectRead,
    summary="Get a project by ID",
    responses={404: {"description": "Project not found"}},
)
async def get_project(
    project_id: UUID,
    current_user: CurrentUser,
    project_service: ProjectServiceDep,
) -> ProjectRead:
    """Retrieve a project by ID. Only the owner can access their projects."""
    try:
        project = await project_service.get_project(project_id, owner_id=current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_read(project)


@router.patch(
    "/{project_id}",
    response_model=ProjectRead,
    summary="Update a project",
    responses={404: {"description": "Project not found"}},
)
async def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    current_user: CurrentUser,
    project_service: ProjectServiceDep,
) -> ProjectRead:
    """Update project metadata. Only the owner can update their projects."""
    try:
        project = await project_service.update_project(
            project_id,
            owner_id=current_user.id,
            name=body.name,
            description=body.description,
            default_voice_model=body.default_voice_model,
            default_language=body.default_language,
            default_llm_model=body.default_llm_model,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _to_read(project)


@router.delete(
    "/{project_id}",
    response_model=MessageResponse,
    summary="Delete a project",
    responses={404: {"description": "Project not found"}},
)
async def delete_project(
    project_id: UUID,
    current_user: CurrentUser,
    project_service: ProjectServiceDep,
) -> MessageResponse:
    """Soft-delete a project and all its videos."""
    try:
        await project_service.delete_project(project_id, owner_id=current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return MessageResponse(message="Project deleted successfully")