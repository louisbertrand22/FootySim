import asyncio

from sqlalchemy import func
from src.footysim.models.goal import Goal
from src.footysim.models.player import Player
import typer
from .db.session import init_models, AsyncSessionLocal
from .seeds.seed_data import seed_minimal
from .services.schedule_service import generate_round_robin
from .services.match_engine import simulate_match
from .models.fixture import Fixture
from .models.club import Club
from .models.match import Match
from sqlalchemy import select, outerjoin
from datetime import date

app = typer.Typer(help="FootySim CLI")


@app.command()
def initdb():
    asyncio.run(init_models())
    typer.echo("Database initialized.")


@app.command()
def seed():
    async def _run():
        async with AsyncSessionLocal() as session:
            await seed_minimal(session)

    asyncio.run(_run())
    typer.echo("Seed data inserted.")


@app.command()
def schedule(
    season_id: int = typer.Argument(..., help="ID de la saison"),
    start_date_opt: str = typer.Option(
        None, "--start-date", help="YYYY-MM-DD (défaut: 2024-08-01)"
    ),
    force: bool = typer.Option(
        False, "--force", help="Supprime les fixtures existantes avant de regénérer"
    ),
    rounds: int = typer.Option(
        2, "--rounds", min=1, max=2, help="1 = aller, 2 = aller/retour"
    ),
):
    """Génère le calendrier de la saison."""
    start = date.fromisoformat(start_date_opt) if start_date_opt else date(2024, 8, 1)

    async def _run():
        async with AsyncSessionLocal() as session:
            count = await generate_round_robin(
                session,
                season_id=season_id,
                start_date=start,
                rounds=rounds,
                clear_existing=force,
            )
            typer.echo(f"{count} fixtures ajoutées.")

    import asyncio

    asyncio.run(_run())


@app.command()
def simulate(fixture_id: int):
    async def _run():
        async with AsyncSessionLocal() as session:
            match = await simulate_match(session, fixture_id)
            typer.echo(f"Result: {match.home_goals} - {match.away_goals}")

    asyncio.run(_run())


@app.command()
def table(season_id: int):
    """Affiche le classement d'une saison avec les noms des clubs."""

    async def _run():
        async with AsyncSessionLocal() as session:
            # 1) Dictionnaire id -> nom de club
            club_rows = await session.execute(
                select(Club.id, Club.name).where(Club.season_id == season_id)
            )
            club_names = dict(club_rows.all())
            if not club_names:
                print("Aucun club pour cette saison.")
                return

            # 2) Récupérer tous les matchs joués de la saison
            rows = await session.execute(
                select(
                    Fixture.home_club_id,
                    Fixture.away_club_id,
                    Match.home_goals,
                    Match.away_goals,
                )
                .join(Fixture, Match.fixture_id == Fixture.id)
                .where(Fixture.season_id == season_id)
            )
            matches = rows.all()
            if not matches:
                print("Aucun match joué pour cette saison.")
                return

            # 3) Cumuler les stats
            table = {
                cid: {
                    "name": club_names.get(cid, f"Club {cid}"),
                    "P": 0,
                    "W": 0,
                    "D": 0,
                    "L": 0,
                    "GF": 0,
                    "GA": 0,
                    "GD": 0,
                    "PTS": 0,
                }
                for cid in club_names.keys()
            }

            for home_id, away_id, hg, ag in matches:
                # home
                th = table[home_id]
                th["P"] += 1
                th["GF"] += hg
                th["GA"] += ag
                # away
                ta = table[away_id]
                ta["P"] += 1
                ta["GF"] += ag
                ta["GA"] += hg
                # résultats
                if hg > ag:
                    th["W"] += 1
                    th["PTS"] += 3
                    ta["L"] += 1
                elif hg < ag:
                    ta["W"] += 1
                    ta["PTS"] += 3
                    th["L"] += 1
                else:
                    th["D"] += 1
                    ta["D"] += 1
                    th["PTS"] += 1
                    ta["PTS"] += 1

            for t in table.values():
                t["GD"] = t["GF"] - t["GA"]

            # 4) Tri: Points, Diff, Buts marqués, Nom
            ordered = sorted(
                table.values(),
                key=lambda t: (-t["PTS"], -t["GD"], -t["GF"], t["name"].lower()),
            )

            # 5) Affichage propre
            header = f"{'#':>2}  {'Club':<22} {'P':>2} {'W':>2} {'D':>2} {'L':>2}  {'GF':>3} {'GA':>3} {'GD':>3}  {'PTS':>3}"
            line = "-" * len(header)
            print(header)
            print(line)
            for i, t in enumerate(ordered, start=1):
                print(
                    f"{i:>2}  {t['name']:<22} {t['P']:>2} {t['W']:>2} {t['D']:>2} {t['L']:>2}  {t['GF']:>3} {t['GA']:>3} {t['GD']:>3}  {t['PTS']:>3}"
                )

    asyncio.run(_run())


@app.command()
def fixtures(season_id: int, round: int | None = None):
    """Affiche les matchs d'une saison (optionnellement filtrés par journée)."""

    async def _run():
        async with AsyncSessionLocal() as session:
            # Map club_id -> name
            club_rows = await session.execute(
                select(Club.id, Club.name).where(Club.season_id == season_id)
            )
            club_names = dict(club_rows.all())

            # LEFT JOIN Fixture <- Match pour avoir aussi les matchs non joués
            j = outerjoin(Fixture, Match, Match.fixture_id == Fixture.id)
            q = (
                select(
                    Fixture.round,
                    Fixture.date,
                    Fixture.home_club_id,
                    Fixture.away_club_id,
                    Match.home_goals,
                    Match.away_goals,
                )
                .select_from(j)
                .where(Fixture.season_id == season_id)
                .order_by(Fixture.round, Fixture.date, Fixture.id)
            )
            if round is not None:
                q = q.where(Fixture.round == round)

            rows = (await session.execute(q)).all()
            if not rows:
                print("Aucun match trouvé.")
                return

            # Groupé par journée
            current = None
            for r, d, h_id, a_id, hg, ag in rows:
                if r != current:
                    current = r
                    print(f"\n=== Journée {r} ===")
                home = club_names.get(h_id, f"Club {h_id}")
                away = club_names.get(a_id, f"Club {a_id}")
                if hg is None or ag is None:
                    print(f"{d} : {home} vs {away}  —  à jouer")
                else:
                    print(f"{d} : {home} {hg}–{ag} {away}")

    asyncio.run(_run())


@app.command()
def simulate_season(
    season_id: int,
    reset: bool = typer.Option(
        False, "--reset", help="Supprime matchs et buts avant de resimuler"
    ),
):
    """(Re)simule tous les matchs d'une saison."""
    import asyncio
    from sqlalchemy import select, delete
    from .db.session import AsyncSessionLocal
    from .models.fixture import Fixture
    from .models.match import Match
    from .models.goal import Goal
    from .services.match_engine import simulate_match

    async def _run():
        async with AsyncSessionLocal() as session:
            if reset:
                # Récupère tous les matchs de la saison
                match_ids = (
                    (
                        await session.execute(
                            select(Match.id)
                            .join(Fixture, Match.fixture_id == Fixture.id)
                            .where(Fixture.season_id == season_id)
                        )
                    )
                    .scalars()
                    .all()
                )
                if match_ids:
                    # Supprime d'abord les buts liés, puis les matchs
                    await session.execute(
                        delete(Goal).where(Goal.match_id.in_(match_ids))
                    )
                    await session.execute(delete(Match).where(Match.id.in_(match_ids)))
                    await session.commit()

            # (Re)charge toutes les fixtures de la saison (il n'existe plus de matchs si --reset)
            fixtures = (
                (
                    await session.execute(
                        select(Fixture)
                        .where(Fixture.season_id == season_id)
                        .order_by(Fixture.round, Fixture.date, Fixture.id)
                    )
                )
                .scalars()
                .all()
            )

            if not fixtures:
                typer.echo("Aucune fixture pour cette saison.")
                return

            # Si pas de reset, ne simuler que celles sans match existant
            if not reset:
                fixtures = [
                    f
                    for f in fixtures
                    if (
                        await session.execute(
                            select(Match.id).where(Match.fixture_id == f.id)
                        )
                    ).scalar_one_or_none()
                    is None
                ]
                if not fixtures:
                    typer.echo(
                        "Rien à simuler (toutes les fixtures ont déjà un résultat)."
                    )
                    return

            for f in fixtures:
                await simulate_match(session, f.id)

    asyncio.run(_run())
    typer.echo(f"Saison {season_id} simulée{' après reset' if reset else ''} !")


@app.command()
def topscorers(season_id: int, limit: int = 10):
    """Top buteurs d'une saison (nécessite la table goal)."""

    async def _run():
        async with AsyncSessionLocal() as session:
            # Goal -> Match -> Fixture (filtre la saison) + Player pour le nom
            q = (
                select(Player.name, func.count(Goal.id).label("goals"))
                .join(Goal, Goal.player_id == Player.id)
                .join(Match, Match.id == Goal.match_id)
                .join(Fixture, Fixture.id == Match.fixture_id)
                .where(Fixture.season_id == season_id, Goal.is_own_goal == False)  # noqa: E712
                .group_by(Player.id, Player.name)
                .order_by(func.count(Goal.id).desc(), Player.name.asc())
                .limit(limit)
            )
            rows = (await session.execute(q)).all()
            if not rows:
                print("Aucun but enregistré pour cette saison.")
                return

            print(f"Top {limit} buteurs — saison {season_id}")
            print("-------------------------------------")
            for i, (name, goals) in enumerate(rows, start=1):
                print(f"{i:>2}. {name:<22} {goals} but(s)")

    asyncio.run(_run())


@app.command("create-season")
def create_season(
    year: str = typer.Argument(..., help="Libellé de la saison, ex: 2019/2020"),
    league_id: int = typer.Option(
        1, "--league-id", "-l", help="ID de la ligue (par défaut 1)"
    ),
):
    """Crée une saison rattachée à une ligue."""
    import asyncio
    from .db.session import AsyncSessionLocal
    from .models.season import Season

    async def _run():
        async with AsyncSessionLocal() as session:
            s = Season(year=year, league_id=league_id)
            session.add(s)
            await session.commit()
            await session.refresh(s)
            typer.echo(
                f"Saison créée: id={s.id}, year={s.year}, league_id={s.league_id}"
            )

    asyncio.run(_run())


if __name__ == "__main__":
    app()
