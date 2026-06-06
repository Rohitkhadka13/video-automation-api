# =============================================================================
# app/domain/repositories/base.py
# Generic abstract repository protocol.
#
# Design:
#   - AbstractRepository[T] is a generic Protocol defining the minimal CRUD
#     contract every concrete repository must satisfy.
#   - Concrete interfaces (IUserRepository, etc.) extend this with
#     domain-specific query methods.
#   - Infrastructure implementations (SQLAlchemy) implement those interfaces.
#
# Using Protocol (structural subtyping) instead of ABC means:
#   - No forced inheritance — any class with matching methods satisfies it.
#   - Better IDE support for type checking.
#   - Easy to swap implementations (SQLAlchemy → in-memory for tests).
# =============================================================================
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

# T is the domain entity type (UserEntity, ProjectEntity, etc.)
T = TypeVar("T")


class AbstractRepository(ABC, Generic[T]):
    """
    Abstract base repository defining the minimal CRUD contract.

    All concrete repository interfaces inherit from this.
    All SQLAlchemy implementations implement the concrete interfaces.

    The Generic[T] parameter is the domain entity type returned by queries,
    NOT the SQLAlchemy model — entities cross layer boundaries, models do not.
    """

    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> T | None:
        """
        Retrieve a single entity by its primary key.

        Returns:
            The entity if found, None otherwise.
            Soft-deleted records return None (treated as non-existent).
        """
        raise NotImplementedError

    @abstractmethod
    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[T]:
        """
        Retrieve a paginated list of entities.

        Args:
            skip:  Number of records to skip (offset).
            limit: Maximum number of records to return.

        Returns:
            List of entities (may be empty).
        """
        raise NotImplementedError

    @abstractmethod
    async def create(self, entity_data: dict) -> T:
        """
        Persist a new entity from a dict of field values.

        Args:
            entity_data: Dict mapping column names to values.

        Returns:
            The created entity with all DB-generated fields populated
            (id, created_at, updated_at).

        Raises:
            AlreadyExistsError: If a unique constraint is violated.
        """
        raise NotImplementedError

    @abstractmethod
    async def update(self, entity_id: UUID, update_data: dict) -> T | None:
        """
        Apply a partial update to an existing entity.

        Args:
            entity_id:   Primary key of the entity to update.
            update_data: Dict of fields to change (only provided fields updated).

        Returns:
            Updated entity, or None if entity_id not found.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, entity_id: UUID) -> bool:
        """
        Hard-delete an entity by primary key.

        For models using SoftDeleteMixin, prefer `soft_delete()` instead.

        Returns:
            True if a record was deleted, False if entity_id not found.
        """
        raise NotImplementedError

    @abstractmethod
    async def count(self) -> int:
        """Return total count of non-deleted entities."""
        raise NotImplementedError


class SoftDeletableRepository(AbstractRepository[T]):
    """
    Extends AbstractRepository with soft-delete operations.
    Inherited by repositories whose models use SoftDeleteMixin.
    """

    @abstractmethod
    async def soft_delete(self, entity_id: UUID) -> bool:
        """
        Mark an entity as deleted by setting deleted_at timestamp.

        Returns:
            True if the entity was found and marked deleted,
            False if entity_id not found or already deleted.
        """
        raise NotImplementedError

    @abstractmethod
    async def restore(self, entity_id: UUID) -> T | None:
        """
        Clear the deleted_at timestamp, restoring a soft-deleted entity.

        Returns:
            Restored entity, or None if not found.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_deleted(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[T]:
        """Return paginated list of soft-deleted entities (admin use)."""
        raise NotImplementedError