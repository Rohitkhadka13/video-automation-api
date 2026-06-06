# =============================================================================
# app/schemas/common.py
# Shared Pydantic schemas reused across multiple endpoints.
# =============================================================================
from __future__ import annotations

from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base for all schemas — strict mode, no extra fields allowed."""
    model_config = ConfigDict(
        from_attributes=True,   # allow ORM → schema conversion
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class MessageResponse(BaseSchema):
    """Generic success message response."""
    message: str


class PaginatedResponse(BaseSchema, Generic[T]):
    """Paginated list wrapper returned by list endpoints."""
    items: list[T]
    total: int
    skip: int
    limit: int

    @property
    def has_more(self) -> bool:
        return self.skip + len(self.items) < self.total


class IDResponse(BaseSchema):
    """Response containing only a resource ID."""
    id: UUID