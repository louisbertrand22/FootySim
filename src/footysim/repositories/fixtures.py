from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .base import AsyncRepository
from ..models.fixture import Fixture


class FixtureRepository(AsyncRepository[Fixture]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Fixture)

    async def by_season_and_round(self, season_id: int, round_: int) -> list[Fixture]:
        res = await self.session.execute(
            select(Fixture).where(
                Fixture.season_id == season_id, Fixture.round == round_
            )
        )
        return list(res.scalars())
