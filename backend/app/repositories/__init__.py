"""
Repository pattern — base interface and abstract repository.

The Repository pattern is the boundary between the domain (services) and the
data access layer (SQLAlchemy). Services depend on repository interfaces, not
on concrete SQLAlchemy session code.

Why this matters:
  - Services can be unit-tested with in-memory fake repositories
  - Switching databases requires only implementing a new repository, not
    rewriting service logic
  - SQL optimization is isolated to repositories, away from business logic

Generic type parameters:
  ModelT         — The SQLAlchemy ORM model class
  CreateSchemaT  — The Pydantic schema for create operations
  UpdateSchemaT  — The Pydantic schema for update operations

Evolution plan:
  Phase 2: Implement SqlAlchemyRepository[ModelT] — concrete base using asyncpg
  Phase 2: Add DocumentRepository, KnowledgeBaseRepository
  Phase 3: Add ChunkRepository with vector similarity search methods
"""

import uuid
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

ModelT = TypeVar("ModelT")
CreateSchemaT = TypeVar("CreateSchemaT")
UpdateSchemaT = TypeVar("UpdateSchemaT")


class BaseRepository(ABC, Generic[ModelT, CreateSchemaT, UpdateSchemaT]):
    """
    Abstract repository interface.

    All concrete repositories MUST implement every method defined here.
    Adding new methods requires updating all concrete implementations.

    The interface uses UUIDs as the identifier type throughout the application.
    """

    @abstractmethod
    async def get_by_id(self, entity_id: uuid.UUID) -> ModelT | None:
        """
        Retrieve a single entity by its UUID primary key.

        Returns None (not raises) if the entity does not exist.
        Route handlers are responsible for converting None → 404.
        """
        ...

    @abstractmethod
    async def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ModelT]:
        """
        Retrieve a paginated list of entities.

        Cursor-based pagination will replace offset pagination in Phase 3
        once collections grow beyond a few thousand records.
        """
        ...

    @abstractmethod
    async def create(self, data: CreateSchemaT) -> ModelT:
        """
        Persist a new entity.

        Returns the created entity with server-generated fields (id, timestamps).
        """
        ...

    @abstractmethod
    async def update(self, entity_id: uuid.UUID, data: UpdateSchemaT) -> ModelT | None:
        """
        Update an existing entity.

        Returns the updated entity, or None if the entity was not found.
        """
        ...

    @abstractmethod
    async def delete(self, entity_id: uuid.UUID) -> bool:
        """
        Delete an entity by UUID.

        Returns True if the entity was found and deleted.
        Returns False if the entity did not exist.
        """
        ...
