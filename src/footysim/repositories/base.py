from typing import Generic, TypeVar, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

T = TypeVar("T")


class AsyncRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model

    async def add(self, entity: T) -> T:
        self.session.add(entity)
        return entity

    async def get(self, id_: int) -> T | None:
        res = await self.session.execute(select(self.model).where(self.model.id == id_))
        return res.scalar_one_or_none()

    async def list(self) -> list[T]:
        res = await self.session.execute(select(self.model))
        return list(res.scalars())
