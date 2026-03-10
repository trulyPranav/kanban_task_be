from typing import Generic, Optional, Type, TypeVar

from sqlalchemy import delete as sa_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic async repository – thin DB-access wrapper."""

    def __init__(self, model: Type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, resource_id: str) -> Optional[ModelType]:
        result = await self.session.execute(
            select(self.model).where(self.model.id == resource_id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def create(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, resource_id: str) -> bool:
        result = await self.session.execute(
            sa_delete(self.model).where(self.model.id == resource_id)  # type: ignore[attr-defined]
        )
        return result.rowcount > 0

    async def count(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()
