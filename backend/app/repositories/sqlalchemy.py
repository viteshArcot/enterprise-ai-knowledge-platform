"""Generic SQLAlchemy repository implementation."""

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.repositories.base import BaseRepository

ModelT = TypeVar("ModelT")
CreateSchemaT = TypeVar("CreateSchemaT")
UpdateSchemaT = TypeVar("UpdateSchemaT")


class BaseSqlAlchemyRepository(BaseRepository[ModelT, CreateSchemaT, UpdateSchemaT]):
    """
    SQLAlchemy implementation of the BaseRepository interface.
    """

    def __init__(self, model_class: type[ModelT], session: AsyncSession) -> None:
        self._model = model_class
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> ModelT | None:
        """Retrieve a single entity by its UUID."""
        return await self._session.get(self._model, entity_id)

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[ModelT]:
        """Retrieve a paginated list of entities."""
        stmt = select(self._model).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, data: CreateSchemaT) -> ModelT:
        """Persist a new entity."""
        if hasattr(data, "model_dump"):
            data_dict = data.model_dump(exclude_unset=True)
        elif isinstance(data, dict):
            data_dict = data
        else:
            raise ValueError("Create schema must be a Pydantic model or dict.")

        entity = self._model(**data_dict)
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def update(self, entity_id: uuid.UUID, data: UpdateSchemaT) -> ModelT | None:
        """Update an existing entity."""
        entity = await self.get_by_id(entity_id)
        if not entity:
            return None

        if hasattr(data, "model_dump"):
            data_dict = data.model_dump(exclude_unset=True)
        elif isinstance(data, dict):
            data_dict = data
        else:
            raise ValueError("Update schema must be a Pydantic model or dict.")

        for key, value in data_dict.items():
            setattr(entity, key, value)

        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def delete(self, entity_id: uuid.UUID) -> bool:
        """Delete an entity by UUID."""
        entity = await self.get_by_id(entity_id)
        if not entity:
            return False
        await self._session.delete(entity)
        await self._session.flush()
        return True
