from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .base import AsyncRepository
from ..models.match import Match


class MatchRepository(AsyncRepository[Match]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Match)

    async def by_fixture(self, fixture_id: int) -> Match | None:
        res = await self.session.execute(
            select(Match).where(Match.fixture_id == fixture_id)
        )
        return res.scalar_one_or_none()
