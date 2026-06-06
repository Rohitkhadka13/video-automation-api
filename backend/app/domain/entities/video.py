# =============================================================================
# app/domain/entities/video.py
# Pure domain entity for Video.
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class VideoEntity:
    """
    Immutable domain representation of a Video.

    Carries both the source file metadata and the processing pipeline
    results. The `processing_metadata` dict is an opaque bag stored
    in JSONB — callers that need typed access cast after reading.
    """

    id: UUID
    title: str
    slug: str
    project_id: UUID
    owner_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

    # Optional source file fields
    description: str | None = field(default=None)
    original_filename: str | None = field(default=None)
    storage_key: str | None = field(default=None)
    mime_type: str | None = field(default=None)
    file_size_bytes: int | None = field(default=None)

    # Processed output fields
    output_storage_key: str | None = field(default=None)
    thumbnail_storage_key: str | None = field(default=None)
    duration_seconds: float | None = field(default=None)
    width: int | None = field(default=None)
    height: int | None = field(default=None)
    fps: float | None = field(default=None)

    # AI pipeline config
    voice_model: str | None = field(default=None)
    language: str | None = field(default=None)
    script_prompt: str | None = field(default=None)

    # Pipeline results
    processing_metadata: dict | None = field(default=None)
    error_message: str | None = field(default=None)
    deleted_at: datetime | None = field(default=None)

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def is_ready(self) -> bool:
        """True when the video has been fully processed and is serveable."""
        return self.status == "completed"

    @property
    def is_processing(self) -> bool:
        return self.status in ("uploading", "uploaded", "processing")

    @property
    def has_failed(self) -> bool:
        return self.status == "failed"

    @property
    def file_size_mb(self) -> float | None:
        if self.file_size_bytes is None:
            return None
        return round(self.file_size_bytes / (1024 * 1024), 2)

    @property
    def resolution(self) -> str | None:
        """Return WxH resolution string, e.g. '1920x1080'."""
        if self.width is not None and self.height is not None:
            return f"{self.width}x{self.height}"
        return None

    @property
    def transcription_text(self) -> str | None:
        """Extract Whisper transcription text from processing_metadata."""
        if self.processing_metadata:
            return self.processing_metadata.get("transcription", {}).get("text")
        return None

    @property
    def generated_script(self) -> str | None:
        """Extract Ollama-generated script from processing_metadata."""
        if self.processing_metadata:
            return self.processing_metadata.get("script", {}).get("text")
        return None

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def with_status(self, status: str, error_message: str | None = None) -> "VideoEntity":
        from dataclasses import replace
        return replace(self, status=status, error_message=error_message)

    def with_storage_key(self, storage_key: str, *, mime_type: str, file_size_bytes: int) -> "VideoEntity":
        from dataclasses import replace
        return replace(
            self,
            storage_key=storage_key,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
        )

    def with_output(
        self,
        *,
        output_storage_key: str,
        thumbnail_storage_key: str | None = None,
        duration_seconds: float | None = None,
        width: int | None = None,
        height: int | None = None,
        fps: float | None = None,
    ) -> "VideoEntity":
        from dataclasses import replace
        return replace(
            self,
            output_storage_key=output_storage_key,
            thumbnail_storage_key=thumbnail_storage_key,
            duration_seconds=duration_seconds,
            width=width,
            height=height,
            fps=fps,
        )

    def with_processing_metadata(self, metadata: dict) -> "VideoEntity":
        from dataclasses import replace
        existing = dict(self.processing_metadata or {})
        existing.update(metadata)
        return replace(self, processing_metadata=existing)

    def __repr__(self) -> str:
        return (
            f"VideoEntity(id={self.id!r}, title={self.title!r}, "
            f"status={self.status!r}, project_id={self.project_id!r})"
        )