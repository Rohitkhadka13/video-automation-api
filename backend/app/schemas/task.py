# =============================================================================
# app/schemas/task.py
# Task request/response schemas.
# =============================================================================
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema


class TaskRead(BaseSchema):
    """Full task detail response."""
    id: UUID
    video_id: UUID
    celery_task_id: str | None
    task_type: str
    status: str
    retry_count: int
    progress: float
    progress_percent: int
    progress_message: str | None
    result_data: dict | None
    error_type: str | None
    error_message: str | None
    log_lines: list[str]
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: float | None
    duration_formatted: str | None
    is_terminal: bool
    created_at: datetime
    updated_at: datetime


class TaskStatusResponse(BaseSchema):
    """Lightweight task status poll response."""
    id: UUID
    status: str
    progress: float
    progress_percent: int
    progress_message: str | None
    is_terminal: bool
    error_message: str | None