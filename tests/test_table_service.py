import pytest
from src.footysim.models.league import League
from src.footysim.models.season import Season
from src.footysim.models.club import Club
from src.footysim.models.fixture import Fixture
from src.footysim.models.match import Match
from src.footysim.services.table_service import build_table


@pytest.mark.asyncio
async def test_table_points(session):
    league = League(name="League T", country="FRA")
    session.add(league)
    await session.flush()
    season = Season(league_id=league.id, year=2024)
    session.add(season)
    await session.flush()

    c1 = Club(season_id=season.id, name="Club1")
    c2 = Club(season_id=season.id, name="Club2")
    session.add_all([c1, c2])
    await session.flush()

    fx = Fixture(
        season_id=season.id,
        round=1,
        date="2024-08-01",
        home_club_id=c1.id,
        away_club_id=c2.id,
    )
    session.add(fx)
    await session.flush()
    session.add(Match(fixture_id=fx.id, home_goals=2, away_goals=1))
    await session.commit()

    table = await build_table(session, season.id)
    assert table[c1.id].pts == 3
    assert table[c2.id].pts == 0
