# =============================================================================
# app/domain/services/video_service.py
# Video upload and lifecycle domain service.
# =============================================================================
from __future__ import annotations

from uuid import UUID

from slugify import slugify

from app.core.config import settings
from app.core.exceptions import (
    FileTooLargeError,
    InvalidFileTypeError,
    NotFoundError,
    ValidationError,
)
from app.core.logging import get_logger
from app.domain.entities.video import VideoEntity
from app.domain.repositories.project_repository import IProjectRepository
from app.domain.repositories.video_repository import IVideoRepository
from app.model.models_video import VideoStatus, VIDEO_STATUS_TRANSITIONS

logger = get_logger(__name__)


class VideoService:
    """Handles video lifecycle: creation, upload validation, status management."""

    def __init__(
        self,
        video_repo: IVideoRepository,
        project_repo: IProjectRepository,
    ) -> None:
        self._video_repo = video_repo
        self._project_repo = project_repo

    async def create_video(
        self,
        *,
        project_id: UUID,
        owner_id: UUID,
        title: str,
        description: str | None = None,
        script_prompt: str | None = None,
        voice_model: str | None = None,
        language: str | None = None,
    ) -> VideoEntity:
        """
        Create a new video record in PENDING state.
        The actual file upload happens separately via the upload endpoint.

        Raises:
            NotFoundError: If the project doesn't exist or isn't owned by owner_id.
        """
        project = await self._project_repo.get_by_id_and_owner(project_id, owner_id)
        if project is None:
            raise NotFoundError(resource="Project", identifier=str(project_id))

        slug = await self._unique_slug(project_id, slugify(title, max_length=500))

        video = await self._video_repo.create(
            {
                "project_id": project_id,
                "owner_id": owner_id,
                "title": title.strip(),
                "slug": slug,
                "description": description,
                "status": VideoStatus.PENDING,
                "script_prompt": script_prompt,
                "voice_model": voice_model or project.default_voice_model,
                "language": language or project.default_language,
            }
        )

        await self._project_repo.increment_video_count(project_id)
        logger.info("video.created", video_id=str(video.id), project_id=str(project_id))
        return video

    def validate_upload(
        self,
        *,
        filename: str,
        content_type: str,
        file_size_bytes: int,
    ) -> None:
        """
        Validate an incoming file upload before persisting.

        Raises:
            FileTooLargeError:    If file exceeds MAX_UPLOAD_SIZE_MB.
            InvalidFileTypeError: If MIME type or extension is not allowed.
        """
        if file_size_bytes > settings.max_upload_size_bytes:
            raise FileTooLargeError(
                max_size_mb=settings.MAX_UPLOAD_SIZE_MB,
                actual_size_mb=file_size_bytes / (1024 * 1024),
            )

        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        allowed_video = settings.ALLOWED_VIDEO_EXTENSIONS
        allowed_audio = settings.ALLOWED_AUDIO_EXTENSIONS
        all_allowed = allowed_video + allowed_audio

        if extension not in all_allowed:
            raise InvalidFileTypeError(allowed=all_allowed, received=extension)

        # Also check MIME type for belt-and-suspenders validation
        allowed_mime_prefixes = ("video/", "audio/")
        if not any(content_type.startswith(p) for p in allowed_mime_prefixes):
            raise InvalidFileTypeError(
                allowed=["video/*", "audio/*"], received=content_type
            )

    async def confirm_upload(
        self,
        video_id: UUID,
        *,
        owner_id: UUID,
        storage_key: str,
        mime_type: str,
        file_size_bytes: int,
    ) -> VideoEntity:
        """
        Called after file storage completes. Updates storage metadata and
        transitions status from UPLOADING → UPLOADED.

        Raises:
            NotFoundError: If video not found or not owned by owner_id.
            ValidationError: If the video is not in UPLOADING state.
        """
        video = await self._get_owned_video(video_id, owner_id)

        if video.status != VideoStatus.UPLOADING:
            raise ValidationError(
                f"Cannot confirm upload: video is in '{video.status}' state, expected 'uploading'"
            )

        await self._video_repo.update_storage_key(
            video_id,
            storage_key=storage_key,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
        )
        await self._video_repo.update_status(video_id, VideoStatus.UPLOADED)

        logger.info("video.upload.confirmed", video_id=str(video_id))
        return await self._get_owned_video(video_id, owner_id)

    async def begin_upload(self, video_id: UUID, *, owner_id: UUID) -> VideoEntity:
        """
        Transition a video from PENDING → UPLOADING.
        Called when the file upload stream starts.
        """
        video = await self._get_owned_video(video_id, owner_id)

        if not VideoStatus(video.status) in VIDEO_STATUS_TRANSITIONS.get(
            VideoStatus.PENDING, set()
        ):
            raise ValidationError(
                f"Cannot begin upload: video is in '{video.status}' state"
            )

        await self._video_repo.update_status(video_id, VideoStatus.UPLOADING)
        return await self._get_owned_video(video_id, owner_id)

    async def get_video(
        self, video_id: UUID, *, project_id: UUID, owner_id: UUID
    ) -> VideoEntity:
        """
        Retrieve a video, enforcing project ownership.

        Raises:
            NotFoundError: If not found or ownership mismatch.
        """
        video = await self._video_repo.get_by_project_and_owner(
            project_id, owner_id, video_id
        )
        if video is None:
            raise NotFoundError(resource="Video", identifier=str(video_id))
        return video

    async def list_videos(
        self,
        project_id: UUID,
        *,
        owner_id: UUID,
        skip: int = 0,
        limit: int = 50,
        status_filter: list[str] | None = None,
    ) -> list[VideoEntity]:
        """Return paginated videos in a project."""
        project = await self._project_repo.get_by_id_and_owner(project_id, owner_id)
        if project is None:
            raise NotFoundError(resource="Project", identifier=str(project_id))

        return await self._video_repo.get_by_project(
            project_id, skip=skip, limit=limit, status_filter=status_filter
        )

    async def delete_video(
        self, video_id: UUID, *, project_id: UUID, owner_id: UUID
    ) -> None:
        """Soft-delete a video and decrement the project counter."""
        video = await self.get_video(video_id, project_id=project_id, owner_id=owner_id)
        await self._video_repo.soft_delete(video_id)
        await self._project_repo.decrement_video_count(project_id)
        logger.info("video.deleted", video_id=str(video_id), project_id=str(project_id))

    async def update_processing_result(
        self,
        video_id: UUID,
        *,
        status: VideoStatus,
        metadata: dict | None = None,
        output_storage_key: str | None = None,
        thumbnail_storage_key: str | None = None,
        duration_seconds: float | None = None,
        width: int | None = None,
        height: int | None = None,
        fps: float | None = None,
        error_message: str | None = None,
    ) -> VideoEntity | None:
        """
        Called by Celery tasks to record processing results.
        Returns the updated entity or None if the video was not found.
        """
        if metadata:
            await self._video_repo.update_processing_metadata(video_id, metadata)

        if output_storage_key:
            await self._video_repo.update_output(
                video_id,
                output_storage_key=output_storage_key,
                thumbnail_storage_key=thumbnail_storage_key,
                duration_seconds=duration_seconds,
                width=width,
                height=height,
                fps=fps,
            )

        await self._video_repo.update_status(
            video_id, status, error_message=error_message
        )

        return await self._video_repo.get_by_id(video_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_owned_video(self, video_id: UUID, owner_id: UUID) -> VideoEntity:
        video = await self._video_repo.get_by_id(video_id)
        if video is None or video.owner_id != owner_id:
            raise NotFoundError(resource="Video", identifier=str(video_id))
        return video

    async def _unique_slug(self, project_id: UUID, base_slug: str) -> str:
        slug = base_slug
        counter = 1
        while True:
            existing = await self._video_repo.get_by_slug(project_id, slug)
            if existing is None:
                return slug
            counter += 1
            slug = f"{base_slug}-{counter}"