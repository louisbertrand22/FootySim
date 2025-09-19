import random
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.fixture import Fixture
from ..models.match import Match
from ..models.player import Player
from ..models.goal import Goal  # <-- buteurs


async def simulate_match(session: AsyncSession, fixture_id: int) -> Match:
    # Récupère le fixture
    fixture = (
        await session.execute(select(Fixture).where(Fixture.id == fixture_id))
    ).scalar_one()

    # Crée le match et flush pour obtenir match.id
    match = Match(fixture_id=fixture.id, home_goals=0, away_goals=0)
    session.add(match)
    await session.flush()  # garantit match.id disponible

    # Pré-charge les joueurs des deux clubs (ids uniquement pour tirage rapide)
    home_players = (
        await session.execute(
            select(
                Player.id, Player.pace, Player.shot, Player.pass_, Player.defend
            ).where(Player.club_id == fixture.home_club_id)
        )
    ).all()
    away_players = (
        await session.execute(
            select(
                Player.id, Player.pace, Player.shot, Player.pass_, Player.defend
            ).where(Player.club_id == fixture.away_club_id)
        )
    ).all()

    def team_strength(rows) -> int:
        """Force = moyenne des 4 attributs, moyennée sur l'effectif."""
        if not rows:
            return 50
        per_player = [(r.pace + r.shot + r.pass_ + r.defend) / 4 for r in rows]
        return int(sum(per_player) / len(per_player))

    sh = team_strength(home_players)
    sa = team_strength(away_players)

    # Probabilité d'un but par minute (simple, à affiner)
    # On met une base faible, modulée par le rapport des forces
    base = 0.015  # ~1.35 buts/équipe/match si forces égales
    p_home = base * (sh / (sa + 1))
    p_away = base * (sa / (sh + 1))

    # Simule minute par minute et enregistre les buteurs
    for minute in range(1, 91):
        if random.random() < p_home:
            match.home_goals += 1
            # Choisit un buteur côté domicile (None si pas de joueurs)
            scorer_id = random.choice(home_players).id if home_players else None
            session.add(
                Goal(
                    match_id=match.id,
                    club_id=fixture.home_club_id,
                    player_id=scorer_id,
                    minute=minute,
                    is_own_goal=False,
                )
            )

        if random.random() < p_away:
            match.away_goals += 1
            scorer_id = random.choice(away_players).id if away_players else None
            session.add(
                Goal(
                    match_id=match.id,
                    club_id=fixture.away_club_id,
                    player_id=scorer_id,
                    minute=minute,
                    is_own_goal=False,
                )
            )

    await session.commit()
    return match
