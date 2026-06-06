# =============================================================================
# app/api/v1/endpoints/tasks.py
# Task status and log endpoints — used for polling during video processing.
# =============================================================================
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, Pagination, get_task_service
from app.core.exceptions import NotFoundError
from app.domain.services.task_service import TaskService
from app.schemas.common import PaginatedResponse
from app.schemas.task import TaskRead, TaskStatusResponse

router = APIRouter()

TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


def _to_read(t: object) -> TaskRead:  # type: ignore[misc]
    return TaskRead(
        id=t.id,
        video_id=t.video_id,
        celery_task_id=t.celery_task_id,
        task_type=t.task_type,
        status=t.status,
        retry_count=t.retry_count,
        progress=t.progress,
        progress_percent=t.progress_percent,
        progress_message=t.progress_message,
        result_data=t.result_data,
        error_type=t.error_type,
        error_message=t.error_message,
        log_lines=t.log_lines,
        started_at=t.started_at,
        completed_at=t.completed_at,
        duration_seconds=t.duration_seconds,
        duration_formatted=t.duration_formatted,
        is_terminal=t.is_terminal,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


@router.get(
    "/{task_id}",
    response_model=TaskRead,
    summary="Get full task details by ID",
    responses={404: {"description": "Task not found"}},
)
async def get_task(
    task_id: UUID,
    current_user: CurrentUser,
    task_service: TaskServiceDep,
) -> TaskRead:
    """
    Retrieve full task details including log lines and result data.

    Only the owner of the associated video can access the task.
    """
    try:
        task = await task_service.get_task(task_id, owner_id=current_user.id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return _to_read(task)


@router.get(
    "/{task_id}/status",
    response_model=TaskStatusResponse,
    summary="Poll task status (lightweight)",
)
async def poll_task_status(
    task_id: UUID,
    current_user: CurrentUser,
    task_service: TaskServiceDep,
) -> TaskStatusResponse:
    """
    Lightweight status poll — returns only status and progress fields.
    Use this for frequent polling (every 1–2 seconds during processing).
    Use `GET /tasks/{id}` when you need log lines or result data.
    """
    try:
        task = await task_service.get_task(task_id, owner_id=current_user.id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return TaskStatusResponse(
        id=task.id,
        status=task.status,
        progress=task.progress,
        progress_percent=task.progress_percent,
        progress_message=task.progress_message,
        is_terminal=task.is_terminal,
        error_message=task.error_message,
    )


@router.get(
    "/video/{video_id}",
    response_model=PaginatedResponse[TaskRead],
    summary="List all tasks for a video",
)
async def list_tasks_for_video(
    video_id: UUID,
    current_user: CurrentUser,
    task_service: TaskServiceDep,
    pagination: Pagination,
) -> PaginatedResponse[TaskRead]:
    """
    Return all task records for a video, newest first.
    Includes all task types and retries.
    """
    try:
        tasks = await task_service.list_tasks_for_video(
            video_id,
            owner_id=current_user.id,
            skip=pagination.skip,
            limit=pagination.limit,
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return PaginatedResponse(
        items=[_to_read(t) for t in tasks],
        total=len(tasks),
        skip=pagination.skip,
        limit=pagination.limit,
    )