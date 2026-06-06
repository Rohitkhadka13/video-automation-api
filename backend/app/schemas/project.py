# =============================================================================
# app/schemas/project.py
# Project request/response schemas.
# =============================================================================
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema


class ProjectCreate(BaseSchema):
    """POST /projects request body."""
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    default_voice_model: str = Field(default="en_US-lessac-medium", max_length=120)
    default_language: str = Field(default="en", max_length=10)
    default_llm_model: str = Field(default="llama3", max_length=120)


class ProjectUpdate(BaseSchema):
    """PATCH /projects/{id} request body — all optional."""
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    default_voice_model: str | None = Field(default=None, max_length=120)
    default_language: str | None = Field(default=None, max_length=10)
    default_llm_model: str | None = Field(default=None, max_length=120)


class ProjectRead(BaseSchema):
    """Project response."""
    id: UUID
    name: str
    slug: str
    description: str | None
    owner_id: UUID
    default_voice_model: str
    default_language: str
    default_llm_model: str
    video_count: int
    created_at: datetime
    updated_at: datetime