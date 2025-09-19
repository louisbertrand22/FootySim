from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .base import AsyncRepository
from ..models.player import Player


class PlayerRepository(AsyncRepository[Player]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Player)

    async def by_club(self, club_id: int) -> list[Player]:
        res = await self.session.execute(
            select(Player).where(Player.club_id == club_id)
        )
        return list(res.scalars())
