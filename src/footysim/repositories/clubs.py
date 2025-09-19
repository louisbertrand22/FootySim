from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .base import AsyncRepository
from ..models.club import Club


class ClubRepository(AsyncRepository[Club]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Club)

    async def by_season(self, season_id: int) -> list[Club]:
        res = await self.session.execute(
            select(Club).where(Club.season_id == season_id)
        )
        return list(res.scalars())
