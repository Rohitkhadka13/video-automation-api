# =============================================================================
# app/domain/entities/task.py
# Pure domain entity for VideoTask.
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class TaskEntity:
    """
    Immutable domain representation of a VideoTask.

    Carries Celery execution metadata and progress information.
    Used by the task service and API polling endpoint.
    """

    id: UUID
    video_id: UUID
    task_type: str
    status: str
    retry_count: int
    progress: float
    created_at: datetime
    updated_at: datetime

    celery_task_id: str | None = field(default=None)
    progress_message: str | None = field(default=None)
    result_data: dict | None = field(default=None)
    error_type: str | None = field(default=None)
    error_message: str | None = field(default=None)
    error_traceback: str | None = field(default=None)
    log: list[str] | None = field(default=None)
    started_at: datetime | None = field(default=None)
    completed_at: datetime | None = field(default=None)
    duration_seconds: float | None = field(default=None)

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def is_terminal(self) -> bool:
        """Return True if the task has reached a final state."""
        return self.status in ("success", "failure", "revoked")

    @property
    def is_running(self) -> bool:
        return self.status in ("pending", "started", "retry")

    @property
    def has_failed(self) -> bool:
        return self.status == "failure"

    @property
    def has_succeeded(self) -> bool:
        return self.status == "success"

    @property
    def progress_percent(self) -> int:
        """Return progress as an integer percentage (0–100)."""
        return int(self.progress * 100)

    @property
    def duration_formatted(self) -> str | None:
        """Return duration as a human-readable string, e.g. '2m 34s'."""
        if self.duration_seconds is None:
            return None
        total = int(self.duration_seconds)
        minutes, seconds = divmod(total, 60)
        if minutes:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    @property
    def log_lines(self) -> list[str]:
        """Return log entries or empty list."""
        return self.log or []

    def __repr__(self) -> str:
        return (
            f"TaskEntity(id={self.id!r}, type={self.task_type!r}, "
            f"status={self.status!r}, progress={self.progress_percent}%)"
        )