# =============================================================================
# app/domain/entities/project.py
# Pure domain entity for Project.
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ProjectEntity:
    """
    Immutable domain representation of a Project.

    A project is the organisational unit that groups related videos and
    holds shared AI pipeline configuration (default voice, language, LLM model).
    """

    id: UUID
    name: str
    slug: str
    owner_id: UUID
    default_voice_model: str
    default_language: str
    default_llm_model: str
    video_count: int
    created_at: datetime
    updated_at: datetime

    description: str | None = field(default=None)
    deleted_at: datetime | None = field(default=None)

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def has_videos(self) -> bool:
        return self.video_count > 0

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def with_updated_details(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        default_voice_model: str | None = None,
        default_language: str | None = None,
        default_llm_model: str | None = None,
    ) -> "ProjectEntity":
        from dataclasses import replace
        return replace(
            self,
            name=name if name is not None else self.name,
            description=description if description is not None else self.description,
            default_voice_model=(
                default_voice_model
                if default_voice_model is not None
                else self.default_voice_model
            ),
            default_language=(
                default_language
                if default_language is not None
                else self.default_language
            ),
            default_llm_model=(
                default_llm_model
                if default_llm_model is not None
                else self.default_llm_model
            ),
        )

    def with_video_count(self, count: int) -> "ProjectEntity":
        from dataclasses import replace
        return replace(self, video_count=max(0, count))

    def __repr__(self) -> str:
        return (
            f"ProjectEntity(id={self.id!r}, name={self.name!r}, "
            f"slug={self.slug!r}, owner_id={self.owner_id!r})"
        )