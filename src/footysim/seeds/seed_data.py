import random
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.country import Country
from ..models.league import League
from ..models.season import Season
from ..models.club import Club
from ..models.player import Player

COUNTRIES = [
    ("FRA", "France"),
    ("ENG", "England"),
    ("ESP", "Spain"),
]

CLUBS = [
    "Paris FC",
    "Olympique Lyonnais",
    "Marseille FC",
    "Chelsea FC",
    "Manchester United",
    "Liverpool FC",
    "Real Madrid",
    "FC Barcelona",
    "Atletico Madrid",
]

POSITIONS = ["GK", "DF", "MF", "FW"]


async def seed_minimal(session: AsyncSession) -> None:
    countries = [Country(code=c, name=n) for c, n in COUNTRIES]
    session.add_all(countries)

    league = League(name="Super League", country="Europe")
    session.add(league)
    await session.flush()

    season = Season(league_id=league.id, year=2024)
    session.add(season)
    await session.flush()

    clubs = []
    for name in CLUBS:
        club = Club(
            season_id=season.id,
            name=name,
            budget=random.randint(20_000_000, 80_000_000),
        )
        clubs.append(club)
    session.add_all(clubs)
    await session.flush()

    for club in clubs:
        for i in range(20):
            player = Player(
                club_id=club.id,
                name=f"Player {club.name[:3]}-{i}",
                age=random.randint(18, 35),
                position=random.choice(POSITIONS),
                pace=random.randint(40, 90),
                shot=random.randint(40, 90),
                pass_=random.randint(40, 90),
                defend=random.randint(40, 90),
            )
            session.add(player)

    await session.commit()
