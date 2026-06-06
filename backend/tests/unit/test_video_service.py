# =============================================================================
# tests/unit/test_video_service.py
# Unit tests for VideoService — all repos mocked.
# =============================================================================
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import (
    FileTooLargeError,
    InvalidFileTypeError,
    NotFoundError,
    ValidationError,
)
from app.domain.entities.project import ProjectEntity
from app.domain.entities.video import VideoEntity
from app.domain.services.video_service import VideoService

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_project(owner_id=None) -> ProjectEntity:
    return ProjectEntity(
        id=uuid4(), name="Test Project", slug="test-project",
        owner_id=owner_id or uuid4(),
        default_voice_model="en_US-lessac-medium",
        default_language="en", default_llm_model="llama3",
        video_count=0,
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    )


def _make_video(owner_id=None, project_id=None, status="pending") -> VideoEntity:
    return VideoEntity(
        id=uuid4(), title="Test Video", slug="test-video",
        project_id=project_id or uuid4(),
        owner_id=owner_id or uuid4(),
        status=status,
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    )


def _make_service(*, project=None, video=None):
    video_repo = MagicMock()
    project_repo = MagicMock()
    video_repo.get_by_id = AsyncMock(return_value=video)
    video_repo.get_by_slug = AsyncMock(return_value=None)
    video_repo.create = AsyncMock(return_value=video or _make_video())
    video_repo.update_status = AsyncMock(return_value=True)
    video_repo.update_storage_key = AsyncMock(return_value=True)
    video_repo.soft_delete = AsyncMock(return_value=True)
    project_repo.get_by_id_and_owner = AsyncMock(return_value=project)
    project_repo.increment_video_count = AsyncMock(return_value=True)
    project_repo.decrement_video_count = AsyncMock(return_value=True)
    service = VideoService(video_repo, project_repo)
    return service, video_repo, project_repo


# =============================================================================
# validate_upload
# =============================================================================

class TestValidateUpload:

    def test_valid_mp4_passes(self):
        service, _, _ = _make_service()
        # Should not raise
        service.validate_upload(
            filename="video.mp4",
            content_type="video/mp4",
            file_size_bytes=10 * 1024 * 1024,   # 10 MB
        )

    def test_file_too_large_raises_error(self):
        service, _, _ = _make_service()
        with pytest.raises(FileTooLargeError):
            service.validate_upload(
                filename="huge.mp4",
                content_type="video/mp4",
                file_size_bytes=600 * 1024 * 1024,   # 600 MB > 500 MB limit
            )

    def test_disallowed_extension_raises_error(self):
        service, _, _ = _make_service()
        with pytest.raises(InvalidFileTypeError):
            service.validate_upload(
                filename="malware.exe",
                content_type="application/octet-stream",
                file_size_bytes=1024,
            )

    def test_invalid_mime_type_raises_error(self):
        service, _, _ = _make_service()
        with pytest.raises(InvalidFileTypeError):
            service.validate_upload(
                filename="file.mp4",
                content_type="application/pdf",
                file_size_bytes=1024,
            )

    def test_audio_file_passes(self):
        service, _, _ = _make_service()
        service.validate_upload(
            filename="audio.mp3",
            content_type="audio/mpeg",
            file_size_bytes=5 * 1024 * 1024,
        )

    @pytest.mark.parametrize("ext", ["mp4", "mov", "avi", "mkv", "webm"])
    def test_all_allowed_video_extensions_pass(self, ext):
        service, _, _ = _make_service()
        service.validate_upload(
            filename=f"video.{ext}",
            content_type="video/mp4",
            file_size_bytes=10 * 1024 * 1024,
        )


# =============================================================================
# create_video
# =============================================================================

class TestCreateVideo:

    async def test_creates_video_when_project_exists(self):
        owner_id = uuid4()
        project = _make_project(owner_id=owner_id)
        video = _make_video(owner_id=owner_id, project_id=project.id)
        service, video_repo, project_repo = _make_service(project=project, video=video)

        result = await service.create_video(
            project_id=project.id,
            owner_id=owner_id,
            title="New Video",
        )

        video_repo.create.assert_awaited_once()
        project_repo.increment_video_count.assert_awaited_once_with(project.id)
        assert result.owner_id == owner_id

    async def test_raises_not_found_when_project_missing(self):
        service, _, project_repo = _make_service(project=None)
        project_repo.get_by_id_and_owner = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError, match="Project"):
            await service.create_video(
                project_id=uuid4(),
                owner_id=uuid4(),
                title="Video",
            )


# =============================================================================
# confirm_upload
# =============================================================================

class TestConfirmUpload:

    async def test_transitions_uploading_to_uploaded(self):
        owner_id = uuid4()
        video = _make_video(owner_id=owner_id, status="uploading")
        updated_video = VideoEntity(
            id=video.id, title=video.title, slug=video.slug,
            project_id=video.project_id, owner_id=owner_id,
            status="uploaded",
            storage_key="uploads/test.mp4",
            mime_type="video/mp4", file_size_bytes=1024,
            created_at=video.created_at, updated_at=datetime.now(UTC),
        )
        service, video_repo, _ = _make_service(video=updated_video)
        video_repo.get_by_id = AsyncMock(side_effect=[video, updated_video])

        result = await service.confirm_upload(
            video.id,
            owner_id=owner_id,
            storage_key="uploads/test.mp4",
            mime_type="video/mp4",
            file_size_bytes=1024,
        )

        video_repo.update_storage_key.assert_awaited_once()
        video_repo.update_status.assert_awaited_once_with(video.id, "uploaded")
        assert result.status == "uploaded"

    async def test_raises_validation_error_when_not_uploading(self):
        owner_id = uuid4()
        video = _make_video(owner_id=owner_id, status="pending")
        service, video_repo, _ = _make_service(video=video)
        video_repo.get_by_id = AsyncMock(return_value=video)

        with pytest.raises(ValidationError, match="uploading"):
            await service.confirm_upload(
                video.id, owner_id=owner_id,
                storage_key="key", mime_type="video/mp4", file_size_bytes=1024,
            )


# =============================================================================
# delete_video
# =============================================================================

class TestDeleteVideo:

    async def test_soft_deletes_and_decrements_count(self):
        owner_id = uuid4()
        project_id = uuid4()
        video = _make_video(owner_id=owner_id, project_id=project_id)
        service, video_repo, project_repo = _make_service(video=video)
        video_repo.get_by_project_and_owner = AsyncMock(return_value=video)

        await service.delete_video(
            video.id, project_id=project_id, owner_id=owner_id
        )

        video_repo.soft_delete.assert_awaited_once_with(video.id)
        project_repo.decrement_video_count.assert_awaited_once_with(project_id)

    async def test_raises_not_found_for_wrong_owner(self):
        service, video_repo, _ = _make_service()
        video_repo.get_by_project_and_owner = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.delete_video(
                uuid4(), project_id=uuid4(), owner_id=uuid4()
            )