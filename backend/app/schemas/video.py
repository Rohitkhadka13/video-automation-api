# =============================================================================
# app/schemas/video.py
# Video request/response schemas.
# =============================================================================
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema


class VideoCreate(BaseSchema):
    """POST /projects/{id}/videos request body."""
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    script_prompt: str | None = Field(default=None, max_length=10000)
    voice_model: str | None = Field(default=None, max_length=120)
    language: str | None = Field(default=None, max_length=10)


class VideoRead(BaseSchema):
    """Video response — full representation."""
    id: UUID
    title: str
    slug: str
    description: str | None
    project_id: UUID
    owner_id: UUID
    status: str
    error_message: str | None
    original_filename: str | None
    mime_type: str | None
    file_size_bytes: int | None
    file_size_mb: float | None
    duration_seconds: float | None
    width: int | None
    height: int | None
    fps: float | None
    resolution: str | None
    voice_model: str | None
    language: str | None
    script_prompt: str | None
    transcription_text: str | None
    generated_script: str | None
    output_url: str | None
    thumbnail_url: str | None
    created_at: datetime
    updated_at: datetime


class VideoStatusResponse(BaseSchema):
    """Lightweight status poll response."""
    id: UUID
    status: str
    error_message: str | None
    progress: float | None = Field(
        default=None,
        description="Latest task progress 0.0–1.0, if available",
    )
    progress_message: str | None = None


class VideoUpdate(BaseSchema):
    """PATCH /videos/{id} — editable metadata only."""
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    script_prompt: str | None = Field(default=None, max_length=10000)
    voice_model: str | None = Field(default=None, max_length=120)
    language: str | None = Field(default=None, max_length=10)


class ProcessVideoRequest(BaseSchema):
    """POST /videos/{id}/process — trigger processing pipeline."""
    force: bool = Field(
        default=False,
        description="Re-process even if already completed",
    )