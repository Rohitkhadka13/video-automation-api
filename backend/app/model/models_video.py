# =============================================================================
# app/models/video.py
# Video SQLAlchemy model + VideoStatus state machine.
# =============================================================================
from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuditMixin, Base, SoftDeleteMixin

if TYPE_CHECKING:
    from app.model.models_project import Project
    from app.model.models_task import VideoTask


class VideoStatus(StrEnum):
    """
    State machine for a video's lifecycle.

    Allowed transitions:
        PENDING   → UPLOADING → UPLOADED → PROCESSING → COMPLETED
                                         ↘             ↘
                                          FAILED        FAILED
        Any state → CANCELLED (user-initiated)
    """
    PENDING     = "pending"       # created, awaiting upload
    UPLOADING   = "uploading"     # file upload in progress
    UPLOADED    = "uploaded"      # file received, queued for processing
    PROCESSING  = "processing"    # Celery task running
    COMPLETED   = "completed"     # all processing done, ready to serve
    FAILED      = "failed"        # processing error
    CANCELLED   = "cancelled"     # user cancelled


# Valid state transitions (from → set of allowed tos)
VIDEO_STATUS_TRANSITIONS: dict[VideoStatus, set[VideoStatus]] = {
    VideoStatus.PENDING:    {VideoStatus.UPLOADING, VideoStatus.CANCELLED},
    VideoStatus.UPLOADING:  {VideoStatus.UPLOADED, VideoStatus.FAILED, VideoStatus.CANCELLED},
    VideoStatus.UPLOADED:   {VideoStatus.PROCESSING, VideoStatus.CANCELLED},
    VideoStatus.PROCESSING: {VideoStatus.COMPLETED, VideoStatus.FAILED, VideoStatus.CANCELLED},
    VideoStatus.COMPLETED:  {VideoStatus.CANCELLED},   # can archive a completed video
    VideoStatus.FAILED:     {VideoStatus.UPLOADED},    # allow retry
    VideoStatus.CANCELLED:  set(),                     # terminal state
}

_video_status_enum = ENUM(
    *[s.value for s in VideoStatus],
    name="video_status",
    create_type=True,
)


class Video(AuditMixin, SoftDeleteMixin, Base):
    """
    Represents a single AI-generated or uploaded video asset.

    Lifecycle:
        1. Created with status=PENDING when the user initiates an upload.
        2. Transitions through UPLOADING → UPLOADED when file storage completes.
        3. A Celery task picks it up → PROCESSING.
        4. On success → COMPLETED; on failure → FAILED.

    The `processing_metadata` JSONB column stores arbitrary pipeline data:
        - Whisper transcription text and segments
        - Ollama-generated script
        - FFmpeg output details (resolution, fps, duration)
        - TTS audio file path
        - Any intermediate file paths
    """

    __tablename__ = "videos"

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(520),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    # ------------------------------------------------------------------
    # Ownership
    # ------------------------------------------------------------------
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    status: Mapped[str] = mapped_column(
        _video_status_enum,
        nullable=False,
        default=VideoStatus.PENDING,
        server_default=VideoStatus.PENDING,
        index=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    # ------------------------------------------------------------------
    # Source file (original upload)
    # ------------------------------------------------------------------
    original_filename: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        default=None,
    )

    storage_key: Mapped[str | None] = mapped_column(
        String(1000),       # relative path or S3 object key
        nullable=True,
        default=None,
    )

    mime_type: Mapped[str | None] = mapped_column(
        String(127),
        nullable=True,
        default=None,
    )

    file_size_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        default=None,
    )

    # ------------------------------------------------------------------
    # Processed output
    # ------------------------------------------------------------------
    output_storage_key: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        default=None,
    )

    thumbnail_storage_key: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        default=None,
    )

    # Video properties (populated after processing)
    duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        default=None,
    )

    width: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)

    # ------------------------------------------------------------------
    # AI pipeline configuration (per-video overrides)
    # ------------------------------------------------------------------
    voice_model: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
        default=None,     # None = use project default
    )

    language: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        default=None,     # None = use project default
    )

    # Prompt text provided by the user to guide Ollama script generation
    script_prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    # ------------------------------------------------------------------
    # Pipeline results — arbitrary structured data in JSONB
    # ------------------------------------------------------------------
    processing_metadata: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="videos",
        lazy="select",
    )

    tasks: Mapped[list["VideoTask"]] = relationship(
        "VideoTask",
        back_populates="video",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="VideoTask.created_at.desc()",
    )

    # ------------------------------------------------------------------
    # Composite indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        Index("ix_videos_project_status", "project_id", "status"),
        Index("ix_videos_owner_status",   "owner_id",   "status"),
        Index("ix_videos_project_slug",   "project_id", "slug", unique=True),
    )

    # ------------------------------------------------------------------
    # State machine helper
    # ------------------------------------------------------------------
    def can_transition_to(self, new_status: VideoStatus) -> bool:
        """Return True if the transition from current status to new_status is allowed."""
        current = VideoStatus(self.status)
        return new_status in VIDEO_STATUS_TRANSITIONS.get(current, set())

    def transition_to(self, new_status: VideoStatus) -> None:
        """
        Transition to new_status, raising ValueError if not allowed.
        This is the only way status should be changed — never set .status directly.
        """
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Invalid status transition: {self.status!r} → {new_status!r}"
            )
        self.status = new_status