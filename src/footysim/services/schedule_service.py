# src/footysim/services/schedule_service.py
from datetime import date, timedelta
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.club import Club
from ..models.fixture import Fixture


async def generate_round_robin(
    session: AsyncSession,
    season_id: int,
    start_date: date,
    rounds: int = 2,
    clear_existing: bool = False,
) -> int:
    """Génère un calendrier round-robin.
    - rounds=1: simple aller
    - rounds=2: aller/retour (domicile/extérieur inversés)
    - clear_existing: True pour supprimer les fixtures existantes d'abord
    Retourne le nombre de fixtures insérées.
    """
    # Optionnellement, purge
    if clear_existing:
        await session.execute(delete(Fixture).where(Fixture.season_id == season_id))
        await session.commit()

    # Clubs de la saison
    clubs = (
        (
            await session.execute(
                select(Club.id).where(Club.season_id == season_id).order_by(Club.id)
            )
        )
        .scalars()
        .all()
    )
    n = len(clubs)
    if n < 2:
        return 0

    # Index des fixtures déjà existantes pour éviter les doublons
    existing = set(
        (r, h, a)
        for (r, h, a) in (
            await session.execute(
                select(Fixture.round, Fixture.home_club_id, Fixture.away_club_id).where(
                    Fixture.season_id == season_id
                )
            )
        ).all()
    )

    # Berger tables (avec bye si impair)
    teams = clubs[:]
    bye = None
    if n % 2 == 1:
        teams.append(bye)
        n += 1

    half = n // 2
    # total_rounds = (n - 1) * rounds
    round_date = start_date
    inserted = 0

    def pairings(arr):
        # appariements de la ronde courante
        for i in range(half):
            yield arr[i], arr[-i - 1]

    # Phase aller (n-1 rondes)
    arr = teams[:]
    for r in range(1, n):  # r = 1..n-1
        round_no = r
        for h, a in pairings(arr):
            if h is None or a is None:
                continue
            # alternance basique pour équilibrer domicile
            home, away = (h, a) if (r % 2 == 1) else (a, h)
            if (round_no, home, away) not in existing:
                session.add(
                    Fixture(
                        season_id=season_id,
                        round=round_no,
                        date=round_date,
                        home_club_id=home,
                        away_club_id=away,
                    )
                )
                existing.add((round_no, home, away))
                inserted += 1
        # rotation
        arr = [arr[0]] + [arr[-1]] + arr[1:-1]
        round_date += timedelta(days=7)

    # Phase retour (si rounds == 2)
    if rounds == 2:
        arr = teams[:]
        for r in range(1, n):
            round_no = (n - 1) + r  # continue la numérotation
            for h, a in pairings(arr):
                if h is None or a is None:
                    continue
                # inversion domicile/extérieur par rapport à l'aller
                home, away = (a, h) if (r % 2 == 1) else (h, a)
                if (round_no, home, away) not in existing:
                    session.add(
                        Fixture(
                            season_id=season_id,
                            round=round_no,
                            date=round_date,
                            home_club_id=home,
                            away_club_id=away,
                        )
                    )
                    existing.add((round_no, home, away))
                    inserted += 1
            arr = [arr[0]] + [arr[-1]] + arr[1:-1]
            round_date += timedelta(days=7)

    await session.commit()
    return inserted
