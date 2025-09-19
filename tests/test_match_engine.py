import pytest
from src.footysim.models.league import League
from src.footysim.models.season import Season
from src.footysim.models.club import Club
from src.footysim.models.fixture import Fixture
from src.footysim.models.player import Player
from src.footysim.services.match_engine import simulate_match


@pytest.mark.asyncio
async def test_simulate_match(session):
    league = League(name="Test League", country="FRA")
    session.add(league)
    await session.flush()
    season = Season(league_id=league.id, year=2024)
    session.add(season)
    await session.flush()

    c1 = Club(season_id=season.id, name="A")
    c2 = Club(season_id=season.id, name="B")
    session.add_all([c1, c2])
    await session.flush()

    for i in range(11):
        session.add(
            Player(
                club_id=c1.id,
                name=f"A{i}",
                age=20 + i,
                position="MF",
                pace=60,
                shot=60,
                pass_=60,
                defend=60,
            )
        )
        session.add(
            Player(
                club_id=c2.id,
                name=f"B{i}",
                age=20 + i,
                position="MF",
                pace=60,
                shot=60,
                pass_=60,
                defend=60,
            )
        )
    await session.flush()

    fx = Fixture(
        season_id=season.id,
        round=1,
        date="2024-08-01",
        home_club_id=c1.id,
        away_club_id=c2.id,
    )
    session.add(fx)
    await session.commit()

    match = await simulate_match(session, fx.id)
    assert match.home_goals >= 0 and match.away_goals >= 0
