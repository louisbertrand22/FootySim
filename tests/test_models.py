import pytest
from src.footysim.models.league import League
from src.footysim.models.season import Season
from src.footysim.models.club import Club


@pytest.mark.asyncio
async def test_create_club(session):
    league = League(name="Test League", country="FRA")
    session.add(league)
    await session.flush()
    season = Season(league_id=league.id, year=2024)
    session.add(season)
    await session.flush()
    club = Club(season_id=season.id, name="Test FC")
    session.add(club)
    await session.commit()
    assert club.id is not None
