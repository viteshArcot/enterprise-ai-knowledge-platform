import uuid
from typing import Generic, TypeVar, Protocol

ModelT = TypeVar("ModelT")
CreateSchemaT = TypeVar("CreateSchemaT", contravariant=True)
UpdateSchemaT = TypeVar("UpdateSchemaT", contravariant=True)

class BaseRepository(Generic[ModelT, CreateSchemaT, UpdateSchemaT]):
    async def get_by_id(self, entity_id: uuid.UUID) -> ModelT | None:
        return None

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[ModelT] | None:
        return None

    async def create(self, data: CreateSchemaT) -> ModelT | None:
        return None

    async def update(self, entity_id: uuid.UUID, data: UpdateSchemaT) -> ModelT | None:
        return None

    async def delete(self, entity_id: uuid.UUID) -> bool | None:
        return None
