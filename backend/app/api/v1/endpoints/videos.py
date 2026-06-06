# =============================================================================
# app/api/v1/endpoints/videos.py
# Video lifecycle endpoints: create, upload, process, list, status, delete.
# =============================================================================
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)

from app.api.deps import CurrentUser, Pagination, get_project_service, get_task_service, get_video_repo
from app.core.config import settings
from app.core.exceptions import (
    FileTooLargeError,
    InvalidFileTypeError,
    NotFoundError,
    ValidationError,
)
from app.core.logging import get_logger
from app.domain.services.project_service import ProjectService
from app.domain.services.task_service import TaskService
from app.domain.services.video_service import VideoService
from app.infrastructure.repositories.sqlalchemy_video_repository import (
    SQLAlchemyVideoRepository,
)
from app.infrastructure.storage.file_storage import FileStorage
from app.model.models_task import TaskType
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.video import (
    ProcessVideoRequest,
    VideoCreate,
    VideoRead,
    VideoStatusResponse,
    VideoUpdate,
)

router = APIRouter()
logger = get_logger(__name__)

VideoRepoDep = Annotated[SQLAlchemyVideoRepository, Depends(get_video_repo)]
ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


def _get_video_service(
    video_repo: VideoRepoDep,
    project_service: ProjectServiceDep,
) -> VideoService:
    from app.infrastructure.repositories.sqlalchemy_project_repository import SQLAlchemyProjectRepository
    return VideoService(video_repo, project_service._project_repo)


VideoServiceDep = Annotated[VideoService, Depends(_get_video_service)]


def _to_read(v: object, storage: FileStorage | None = None) -> VideoRead:  # type: ignore[misc]
    output_url = None
    thumbnail_url = None
    if storage:
        if v.output_storage_key:
            output_url = storage.public_url(v.output_storage_key)
        if v.thumbnail_storage_key:
            thumbnail_url = storage.public_url(v.thumbnail_storage_key)

    return VideoRead(
        id=v.id, title=v.title, slug=v.slug, description=v.description,
        project_id=v.project_id, owner_id=v.owner_id, status=v.status,
        error_message=v.error_message, original_filename=v.original_filename,
        mime_type=v.mime_type, file_size_bytes=v.file_size_bytes,
        file_size_mb=v.file_size_mb, duration_seconds=v.duration_seconds,
        width=v.width, height=v.height, fps=v.fps, resolution=v.resolution,
        voice_model=v.voice_model, language=v.language,
        script_prompt=v.script_prompt,
        transcription_text=v.transcription_text,
        generated_script=v.generated_script,
        output_url=output_url,
        thumbnail_url=thumbnail_url,
        created_at=v.created_at, updated_at=v.updated_at,
    )


@router.post(
    "/projects/{project_id}/videos",
    response_model=VideoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new video record",
    tags=["videos"],
)
async def create_video(
    project_id: UUID,
    body: VideoCreate,
    current_user: CurrentUser,
    video_service: VideoServiceDep,
) -> VideoRead:
    """
    Create a new video record in PENDING state.
    Follow up with `POST /videos/{id}/upload` to attach the source file.
    """
    try:
        video = await video_service.create_video(
            project_id=project_id,
            owner_id=current_user.id,
            title=body.title,
            description=body.description,
            script_prompt=body.script_prompt,
            voice_model=body.voice_model,
            language=body.language,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return _to_read(video)


@router.post(
    "/{video_id}/upload",
    response_model=VideoRead,
    summary="Upload source file for a video",
    responses={
        413: {"description": "File too large"},
        422: {"description": "Unsupported file type"},
    },
)
async def upload_video(
    video_id: UUID,
    current_user: CurrentUser,
    video_service: VideoServiceDep,
    file: UploadFile = File(..., description="Video or audio file to upload"),
) -> VideoRead:
    """
    Upload the source file for a video record.

    Supported formats: mp4, mov, avi, mkv, webm, mp3, wav, aac, ogg, m4a.
    Maximum file size: configured via MAX_UPLOAD_SIZE_MB (default 500MB).

    The video transitions: PENDING → UPLOADING → UPLOADED.
    """
    content_type = file.content_type or "application/octet-stream"
    filename = file.filename or "upload"

    # Read file into memory to get size (could stream to disk for very large files)
    content = await file.read()
    file_size = len(content)

    try:
        video_service.validate_upload(
            filename=filename,
            content_type=content_type,
            file_size_bytes=file_size,
        )
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except InvalidFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    # Transition to UPLOADING
    try:
        await video_service.begin_upload(video_id, owner_id=current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    # Store the file
    storage = FileStorage()
    import io
    storage_key = await storage.upload(
        io.BytesIO(content),
        prefix=f"uploads/{current_user.id}",
        original_filename=filename,
        content_type=content_type,
    )

    # Confirm upload → UPLOADED
    video = await video_service.confirm_upload(
        video_id,
        owner_id=current_user.id,
        storage_key=storage_key,
        mime_type=content_type,
        file_size_bytes=file_size,
    )

    logger.info(
        "video.uploaded",
        video_id=str(video_id),
        size_mb=round(file_size / (1024 * 1024), 2),
        content_type=content_type,
    )
    return _to_read(video, storage)


@router.post(
    "/{video_id}/process",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger the AI processing pipeline",
    responses={
        404: {"description": "Video not found"},
        409: {"description": "Video not in a processable state"},
    },
)
async def process_video(
    video_id: UUID,
    current_user: CurrentUser,
    video_service: VideoServiceDep,
    task_service: TaskServiceDep,
    body: ProcessVideoRequest | None = None,
) -> dict:
    """
    Enqueue the full AI processing pipeline for a video.

    Pipeline: Whisper transcription → Ollama script → Piper TTS → FFmpeg merge.

    The response contains a `task_id` you can poll via `GET /tasks/{task_id}`.
    Processing is asynchronous — this endpoint returns immediately (HTTP 202).
    """
    # Verify video exists and is owned by the user
    try:
        video = await video_service._get_owned_video(video_id, current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    # Only allow processing from UPLOADED or FAILED (retry) state
    if video.status not in ("uploaded", "failed"):
        if not (body and body.force and video.status == "completed"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Video is in '{video.status}' state. "
                       f"Only 'uploaded' or 'failed' videos can be processed.",
            )

    # Create the task record
    task = await task_service.create_task(video_id, TaskType.VIDEO_PROCESS)

    # Enqueue the Celery task
    from app.infrastructure.celery.tasks.video_tasks import process_video as celery_task
    celery_result = celery_task.apply_async(
        args=[str(video_id), str(task.id)],
        queue=settings.CELERY_VIDEO_QUEUE,
    )

    # Bind the Celery task ID to the DB record
    await task_service.bind_celery_id(task.id, celery_result.id)

    logger.info(
        "video.process.enqueued",
        video_id=str(video_id),
        task_id=str(task.id),
        celery_task_id=celery_result.id,
    )

    return {
        "message": "Processing enqueued",
        "task_id": str(task.id),
        "celery_task_id": celery_result.id,
        "video_id": str(video_id),
    }


@router.get(
    "/{video_id}/status",
    response_model=VideoStatusResponse,
    summary="Poll processing status",
)
async def get_video_status(
    video_id: UUID,
    current_user: CurrentUser,
    video_service: VideoServiceDep,
    task_service: TaskServiceDep,
) -> VideoStatusResponse:
    """
    Lightweight status endpoint for polling during processing.
    Returns the video's current status and the latest task's progress.
    """
    try:
        video = await video_service._get_owned_video(video_id, current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    latest_task = await task_service.get_latest_task(
        video_id, owner_id=current_user.id
    )

    return VideoStatusResponse(
        id=video.id,
        status=video.status,
        error_message=video.error_message,
        progress=latest_task.progress if latest_task else None,
        progress_message=latest_task.progress_message if latest_task else None,
    )


@router.get(
    "/projects/{project_id}/videos",
    response_model=PaginatedResponse[VideoRead],
    summary="List videos in a project",
    tags=["videos"],
)
async def list_videos(
    project_id: UUID,
    current_user: CurrentUser,
    video_service: VideoServiceDep,
    pagination: Pagination,
    status_filter: list[str] | None = Query(default=None),
) -> PaginatedResponse[VideoRead]:
    """Return paginated videos in a project, with optional status filtering."""
    storage = FileStorage()
    try:
        videos = await video_service.list_videos(
            project_id,
            owner_id=current_user.id,
            skip=pagination.skip,
            limit=pagination.limit,
            status_filter=status_filter,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    from app.infrastructure.repositories.sqlalchemy_video_repository import SQLAlchemyVideoRepository
    total = await video_service._video_repo.count_by_project(
        project_id, status_filter=status_filter
    )

    return PaginatedResponse(
        items=[_to_read(v, storage) for v in videos],
        total=total, skip=pagination.skip, limit=pagination.limit,
    )


@router.get(
    "/{video_id}",
    response_model=VideoRead,
    summary="Get a video by ID",
    responses={404: {"description": "Video not found"}},
)
async def get_video(
    video_id: UUID,
    current_user: CurrentUser,
    video_service: VideoServiceDep,
    project_id: UUID = Query(...),
) -> VideoRead:
    """Retrieve a video by ID. Requires the project_id as a query parameter."""
    storage = FileStorage()
    try:
        video = await video_service.get_video(
            video_id, project_id=project_id, owner_id=current_user.id
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_read(video, storage)


@router.delete(
    "/{video_id}",
    response_model=MessageResponse,
    summary="Delete a video",
    responses={404: {"description": "Video not found"}},
)
async def delete_video(
    video_id: UUID,
    current_user: CurrentUser,
    video_service: VideoServiceDep,
    project_id: UUID = Query(...),
) -> MessageResponse:
    """Soft-delete a video and decrement the project's video count."""
    try:
        await video_service.delete_video(
            video_id, project_id=project_id, owner_id=current_user.id
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return MessageResponse(message="Video deleted successfully")