from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.match import Match
from ..models.fixture import Fixture


@dataclass
class TableRow:
    club_id: int
    played: int = 0
    won: int = 0
    draw: int = 0
    lost: int = 0
    gf: int = 0
    ga: int = 0
    pts: int = 0


async def build_table(session: AsyncSession, season_id: int) -> dict[int, TableRow]:
    rows: dict[int, TableRow] = {}
    res = await session.execute(
        select(Match, Fixture)
        .join(Fixture, Fixture.id == Match.fixture_id)
        .where(Fixture.season_id == season_id)
    )
    for match, fixture in res.all():
        home = rows.setdefault(
            fixture.home_club_id, TableRow(club_id=fixture.home_club_id)
        )
        away = rows.setdefault(
            fixture.away_club_id, TableRow(club_id=fixture.away_club_id)
        )
        home.played += 1
        away.played += 1
        home.gf += match.home_goals
        home.ga += match.away_goals
        away.gf += match.away_goals
        away.ga += match.home_goals
        if match.home_goals > match.away_goals:
            home.won += 1
            away.lost += 1
            home.pts += 3
        elif match.home_goals < match.away_goals:
            away.won += 1
            home.lost += 1
            away.pts += 3
        else:
            home.draw += 1
            away.draw += 1
            home.pts += 1
            away.pts += 1
    return rows
