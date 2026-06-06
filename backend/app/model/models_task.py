# =============================================================================
# app/models/task.py
# VideoTask SQLAlchemy model — tracks Celery task execution.
# One Video can have multiple task records (initial + retries).
# =============================================================================
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuditMixin, Base

if TYPE_CHECKING:
    from app.model.models_video import Video


class TaskStatus(StrEnum):
    PENDING   = "pending"     # enqueued in Redis, not yet picked up
    STARTED   = "started"     # worker has begun processing
    RETRY     = "retry"       # failed, scheduled for retry
    SUCCESS   = "success"     # completed successfully
    FAILURE   = "failure"     # all retries exhausted
    REVOKED   = "revoked"     # manually cancelled


class TaskType(StrEnum):
    VIDEO_PROCESS    = "video_process"      # full pipeline
    TRANSCRIPTION    = "transcription"      # Whisper only
    TTS              = "tts"                # Piper TTS only
    THUMBNAIL        = "thumbnail"          # FFmpeg thumbnail
    SCRIPT_GENERATE  = "script_generate"   # Ollama script generation


_task_status_enum = ENUM(
    *[s.value for s in TaskStatus],
    name="task_status",
    create_type=True,
)

_task_type_enum = ENUM(
    *[t.value for t in TaskType],
    name="task_type",
    create_type=True,
)


class VideoTask(AuditMixin, Base):
    """
    Records execution details for every Celery task dispatched for a video.

    Design:
        - Celery task ID (`celery_task_id`) links back to the broker.
        - `result_data` (JSONB) stores task-type-specific output:
            transcription → {"text": ..., "segments": [...]}
            tts           → {"audio_path": ..., "duration": ...}
            video_process → {"output_path": ..., "duration": ...}
        - `progress` (0.0–1.0) enables real-time progress bars via polling.
        - `log` accumulates human-readable step messages for the UI.
    """

    __tablename__ = "video_tasks"

    # ------------------------------------------------------------------
    # References
    # ------------------------------------------------------------------
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Celery integration
    # ------------------------------------------------------------------
    celery_task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
        unique=True,        # one DB record per Celery task ID
        index=True,
    )

    task_type: Mapped[str] = mapped_column(
        _task_type_enum,
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Status tracking
    # ------------------------------------------------------------------
    status: Mapped[str] = mapped_column(
        _task_status_enum,
        nullable=False,
        default=TaskStatus.PENDING,
        server_default=TaskStatus.PENDING,
        index=True,
    )

    # Retry counter — incremented each time Celery retries the task
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    # ------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # Processing time in seconds (populated on completion)
    duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        default=None,
    )

    # ------------------------------------------------------------------
    # Progress & output
    # ------------------------------------------------------------------
    # 0.0 = not started, 1.0 = complete
    progress: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0.0",
    )

    # Human-readable progress message ("Transcribing audio...", "Rendering video...")
    progress_message: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        default=None,
    )

    # Structured task output (type-specific payload)
    result_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )

    # Error details on failure
    error_type: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    # Full traceback (dev/staging only — truncated in production)
    error_traceback: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    # Append-only log of processing steps (list of strings in JSONB)
    log: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        server_default="'[]'::jsonb",
    )

    # ------------------------------------------------------------------
    # Relationship
    # ------------------------------------------------------------------
    video: Mapped["Video"] = relationship(
        "Video",
        back_populates="tasks",
        lazy="select",
    )

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        Index("ix_video_tasks_video_status",  "video_id", "status"),
        Index("ix_video_tasks_video_type",    "video_id", "task_type"),
        Index("ix_video_tasks_celery_status", "celery_task_id", "status"),
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def mark_started(self) -> None:
        self.status = TaskStatus.STARTED
        self.started_at = datetime.now(UTC)

    def mark_success(self, result: dict | None = None) -> None:
        self.status = TaskStatus.SUCCESS
        self.completed_at = datetime.now(UTC)
        self.progress = 1.0
        if result:
            self.result_data = result
        if self.started_at:
            self.duration_seconds = (
                self.completed_at - self.started_at
            ).total_seconds()

    def mark_failure(
        self,
        error_type: str,
        error_message: str,
        traceback: str | None = None,
    ) -> None:
        self.status = TaskStatus.FAILURE
        self.completed_at = datetime.now(UTC)
        self.error_type = error_type
        self.error_message = error_message
        self.error_traceback = traceback
        if self.started_at:
            self.duration_seconds = (
                self.completed_at - self.started_at
            ).total_seconds()

    def append_log(self, message: str) -> None:
        """Append a step message to the task log."""
        current: list = self.log or []
        self.log = [*current, f"{datetime.now(UTC).isoformat()} — {message}"]

    def update_progress(self, value: float, message: str | None = None) -> None:
        """Update progress (0.0–1.0) and optional message."""
        self.progress = max(0.0, min(1.0, value))
        if message:
            self.progress_message = message