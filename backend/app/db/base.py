# =============================================================================
# app/db/base.py
# SQLAlchemy 2.0 declarative base and reusable model mixins.
#
# All models import Base from here so Alembic's env.py can do:
#   from app.db.base import Base
#   import app.models   # noqa — side-effect: registers metadata
#   target_metadata = Base.metadata
# =============================================================================
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedColumn, mapped_column


class Base(DeclarativeBase):
    """
    Project-wide SQLAlchemy declarative base.

    All models inherit from this class. By centralising it here:
      - Alembic can discover all table metadata from one import.
      - Shared type overrides (e.g. UUID rendering) live in one place.
    """

    # Override default type map: Python uuid.UUID → PostgreSQL UUID (not CHAR(32))
    type_annotation_map: dict[Any, Any] = {
        uuid.UUID: UUID(as_uuid=True),
    }

    def __repr__(self) -> str:
        """Generic repr — shows table name and primary key for debugging."""
        pk_cols = [c.name for c in self.__table__.primary_key.columns]
        pk_vals = {col: getattr(self, col, "?") for col in pk_cols}
        pairs = ", ".join(f"{k}={v!r}" for k, v in pk_vals.items())
        return f"<{type(self).__name__}({pairs})>"

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict of all column values. Useful for logging/debugging."""
        return {col.name: getattr(self, col.name) for col in self.__table__.columns}


# ---------------------------------------------------------------------------
# Mixins — composable model traits
# ---------------------------------------------------------------------------

class UUIDPrimaryKeyMixin:
    """
    Adds a UUID v4 primary key column named `id`.
    Generated server-side by PostgreSQL's gen_random_uuid() so the DB is
    the authoritative source, but also set as a Python default so we can
    reference the id before flushing to the DB.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        index=True,
    )


class TimestampMixin:
    """
    Adds `created_at` and `updated_at` columns managed automatically by the DB.

    - created_at: set once on INSERT via server_default.
    - updated_at: set on INSERT and refreshed on every UPDATE via onupdate.

    Using server-side defaults (PostgreSQL NOW()) guarantees consistency even
    if records are inserted outside SQLAlchemy (e.g. raw SQL seeds, Alembic data migrations).
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        # Also set Python-side so in-memory objects have the value before DB flush
        default=lambda: datetime.now(UTC),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class SoftDeleteMixin:
    """
    Adds `deleted_at` for soft-delete pattern.
    Records with a non-NULL deleted_at are considered logically deleted.
    Repositories must filter on deleted_at IS NULL for normal queries.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        self.deleted_at = datetime.now(UTC)

    def restore(self) -> None:
        self.deleted_at = None


class AuditMixin(UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Convenience mixin combining UUID PK + timestamps.
    The most common mixin combination — used by all four domain models.
    """