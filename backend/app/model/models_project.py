# =============================================================================
# app/models/project.py
# Project SQLAlchemy model.
# A project is a named container that groups related videos together.
# =============================================================================
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuditMixin, Base, SoftDeleteMixin

if TYPE_CHECKING:
    from app.model.models_user import User
    from app.model.models_video import Video


class Project(AuditMixin, SoftDeleteMixin, Base):
    """
    A project groups videos and stores shared configuration (e.g. default
    voice model, script style, output settings).

    Relationships:
        owner:  many-to-one → User
        videos: one-to-many → Video
    """

    __tablename__ = "projects"

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(280),
        nullable=False,
        index=True,
        # Slug is owner-scoped: the same slug can exist in different owners.
        # Unique constraint is defined in __table_args__ below (composite).
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    # ------------------------------------------------------------------
    # Ownership
    # ------------------------------------------------------------------
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Project-level defaults (overridable per-video)
    # ------------------------------------------------------------------
    default_voice_model: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default="en_US-lessac-medium",
        server_default="en_US-lessac-medium",
    )

    default_language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="en",
        server_default="en",
    )

    default_llm_model: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default="llama3",
        server_default="llama3",
    )

    # ------------------------------------------------------------------
    # Counters (denormalised for fast listing)
    # ------------------------------------------------------------------
    video_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="projects",
        lazy="select",
    )

    videos: Mapped[list["Video"]] = relationship(
        "Video",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="Video.created_at.desc()",
    )

    # ------------------------------------------------------------------
    # Constraints and indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # Slug unique per owner — allows same slug across different users
        Index("uix_projects_owner_slug", "owner_id", "slug", unique=True),
        Index("ix_projects_owner_created", "owner_id", "created_at"),
    )