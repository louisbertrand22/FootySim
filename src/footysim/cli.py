# src/footysim/cli.py
from __future__ import annotations

import asyncio
from datetime import date
from typing import Optional, Dict

import typer
from sqlalchemy import select, delete, outerjoin, func

from .db.session import init_models, AsyncSessionLocal
from .seeds.seed_data import seed_minimal
from .services.schedule_service import generate_round_robin
from .services.match_engine import simulate_match

from .models.club import Club
from .models.fixture import Fixture
from .models.goal import Goal
from .models.match import Match
from .models.player import Player
from .models.season import Season

app = typer.Typer(help="FootySim CLI")


# ---------- Helpers ----------

def run_async(coro):
    """Exécute une coroutine avec asyncio.run en un seul endroit."""
    asyncio.run(coro)


async def _get_club_names(session, season_id: int) -> Dict[int, str]:
    rows = await session.execute(
        select(Club.id, Club.name).where(Club.season_id == season_id)
    )
    return dict(rows.all())


async def _ensure_season_exists(session, season_id: int) -> Optional[Season]:
    s = await session.get(Season, season_id)
    return s


# ---------- Commands ----------

@app.command()
def initdb():
    """Crée / met à jour le schéma de la base (toutes les tables)."""
    run_async(init_models())
    typer.echo("✅ Base initialisée.")

@app.command(name="init-db")
def init_db_alias():
    """Alias de initdb."""
    run_async(init_models())
    typer.echo("✅ Base initialisée.")


@app.command()
def seed():
    """Insère des données minimales de test (ligue/clubs/joueurs)."""
    async def _run():
        async with AsyncSessionLocal() as session:
            await seed_minimal(session)
    run_async(_run())
    typer.echo("🌱 Données de seed insérées.")


@app.command()
def schedule(
    season_id: int = typer.Argument(..., help="ID de la saison"),
    start_date: Optional[str] = typer.Option(
        None, "--start-date", help="Date de début (YYYY-MM-DD). Défaut: 2024-08-01"
    ),
    force: bool = typer.Option(
        False, "--force", help="Supprime les fixtures existantes avant de regénérer"
    ),
    rounds: int = typer.Option(2, "--rounds", min=1, max=2, help="1=aller, 2=aller/retour"),
):
    """Génère le calendrier (round-robin) pour une saison."""
    start = date.fromisoformat(start_date) if start_date else date(2024, 8, 1)

    async def _run():
        async with AsyncSessionLocal() as session:
            if not await _ensure_season_exists(session, season_id):
                typer.echo(f"❌ Saison {season_id} inexistante.")
                return
            club_names = await _get_club_names(session, season_id)
            if not club_names:
                typer.echo("❌ Aucun club dans cette saison – seed ou ajoute des clubs d’abord.")
                return

            count = await generate_round_robin(
                session,
                season_id=season_id,
                start_date=start,
                rounds=rounds,
                clear_existing=force,
            )
            typer.echo(f"📅 {count} fixtures ajoutées pour la saison {season_id}.")

    run_async(_run())


@app.command()
def simulate(fixture_id: int):
    """Simule un match (par fixture id) et affiche le score + clubs."""
    async def _run():
        async with AsyncSessionLocal() as session:
            fxt = await session.get(Fixture, fixture_id)
            if not fxt:
                typer.echo(f"❌ Fixture {fixture_id} introuvable.")
                return

            match = await simulate_match(session, fixture_id)

            # Affichage avec noms des clubs
            home = await session.get(Club, fxt.home_club_id)
            away = await session.get(Club, fxt.away_club_id)
            hname = home.name if home else f"Club {fxt.home_club_id}"
            aname = away.name if away else f"Club {fxt.away_club_id}"

            typer.echo(f"🏟️  {hname} {match.home_goals} – {match.away_goals} {aname}")

    run_async(_run())


@app.command()
def table(season_id: int):
    """Affiche le classement d'une saison (points, diff, etc.) avec noms de clubs."""
    async def _run():
        async with AsyncSessionLocal() as session:
            if not await _ensure_season_exists(session, season_id):
                typer.echo(f"❌ Saison {season_id} inexistante.")
                return

            club_names = await _get_club_names(session, season_id)
            if not club_names:
                typer.echo("❌ Aucun club pour cette saison.")
                return

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
                typer.echo("ℹ️ Aucun match joué pour cette saison.")
                return

            table = {
                cid: {
                    "name": club_names.get(cid, f"Club {cid}"),
                    "P": 0, "W": 0, "D": 0, "L": 0,
                    "GF": 0, "GA": 0, "GD": 0, "PTS": 0,
                }
                for cid in club_names.keys()
            }

            for home_id, away_id, hg, ag in matches:
                th = table[home_id]
                ta = table[away_id]
                th["P"] += 1
                ta["P"] += 1
                th["GF"] += hg
                th["GA"] += ag
                ta["GF"] += ag
                ta["GA"] += hg

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

            ordered = sorted(
                table.values(),
                key=lambda t: (-t["PTS"], -t["GD"], -t["GF"], t["name"].lower()),
            )

            header = f"{'#':>2}  {'Club':<22} {'P':>2} {'W':>2} {'D':>2} {'L':>2}  {'GF':>3} {'GA':>3} {'GD':>3}  {'PTS':>3}"
            line = "-" * len(header)
            print(header)
            print(line)
            for i, t in enumerate(ordered, start=1):
                print(
                    f"{i:>2}  {t['name']:<22} {t['P']:>2} {t['W']:>2} {t['D']:>2} {t['L']:>2}  {t['GF']:>3} {t['GA']:>3} {t['GD']:>3}  {t['PTS']:>3}"
                )

    run_async(_run())


@app.command()
def fixtures(season_id: int, round: Optional[int] = typer.Option(None, "--round")):
    """Affiche les fixtures d'une saison (optionnellement filtrées par journée)."""
    async def _run():
        async with AsyncSessionLocal() as session:
            if not await _ensure_season_exists(session, season_id):
                typer.echo(f"❌ Saison {season_id} inexistante.")
                return

            club_names = await _get_club_names(session, season_id)
            if not club_names:
                typer.echo("❌ Aucun club pour cette saison.")
                return

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
                typer.echo("ℹ️ Aucune fixture trouvée.")
                return

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

    run_async(_run())


@app.command("simulate-season")
def simulate_season(
    season_id: int,
    reset: bool = typer.Option(False, "--reset", help="Supprime matchs et buts avant de resimuler"),
):
    """(Re)simule tous les matchs d'une saison. Par défaut, ne simule que les fixtures non jouées."""
    async def _run():
        async with AsyncSessionLocal() as session:
            if not await _ensure_season_exists(session, season_id):
                typer.echo(f"❌ Saison {season_id} inexistante.")
                return

            if reset:
                match_ids = (
                    (
                        await session.execute(
                            select(Match.id)
                            .join(Fixture, Match.fixture_id == Fixture.id)
                            .where(Fixture.season_id == season_id)
                        )
                    ).scalars().all()
                )
                if match_ids:
                    await session.execute(delete(Goal).where(Goal.match_id.in_(match_ids)))
                    await session.execute(delete(Match).where(Match.id.in_(match_ids)))
                    await session.commit()

            fixtures = (
                (
                    await session.execute(
                        select(Fixture)
                        .where(Fixture.season_id == season_id)
                        .order_by(Fixture.round, Fixture.date, Fixture.id)
                    )
                ).scalars().all()
            )
            if not fixtures:
                typer.echo("❌ Aucune fixture pour cette saison. Lance d’abord la commande 'schedule'.")
                return

            if not reset:
                fixtures = [
                    f for f in fixtures
                    if (
                        await session.execute(
                            select(Match.id).where(Match.fixture_id == f.id)
                        )
                    ).scalar_one_or_none() is None
                ]
                if not fixtures:
                    typer.echo("ℹ️ Rien à simuler (toutes les fixtures ont déjà un résultat).")
                    return

            for f in fixtures:
                await simulate_match(session, f.id)

    run_async(_run())
    typer.echo(f"🎲 Saison {season_id} simulée{' après reset' if reset else ''} !")

@app.command("simulate-round")
def simulate_round(
    season_id: int = typer.Argument(..., help="ID de la saison"),
    round: int = typer.Argument(..., help="Numéro de la journée à simuler"),
    reset: bool = typer.Option(False, "--reset", help="Supprime matchs/buts de cette journée avant de resimuler"),
):
    """(Re)simule uniquement une journée d'une saison."""
    import asyncio
    from sqlalchemy import select, delete
    from .db.session import AsyncSessionLocal
    from .models.fixture import Fixture
    from .models.match import Match
    from .models.goal import Goal
    from .services.match_engine import simulate_match

    async def _run():
        async with AsyncSessionLocal() as session:
            # Récupère les fixtures de la journée
            fixture_ids = (
                (
                    await session.execute(
                        select(Fixture.id)
                        .where(Fixture.season_id == season_id, Fixture.round == round)
                        .order_by(Fixture.date, Fixture.id)
                    )
                )
                .scalars()
                .all()
            )

            if not fixture_ids:
                typer.echo(f"Aucune fixture pour saison {season_id}, journée {round}.")
                return

            if reset:
                # Supprime matchs + buts liés à ces fixtures
                match_ids = (
                    (
                        await session.execute(
                            select(Match.id).where(Match.fixture_id.in_(fixture_ids))
                        )
                    )
                    .scalars()
                    .all()
                )
                if match_ids:
                    await session.execute(delete(Goal).where(Goal.match_id.in_(match_ids)))
                    await session.execute(delete(Match).where(Match.id.in_(match_ids)))
                    await session.commit()

            # Simule chaque fixture
            done = 0
            for fid in fixture_ids:
                await simulate_match(session, fid)
                done += 1

            typer.echo(f"Journée {round} simulée ({done} match(s)).")

    asyncio.run(_run())


@app.command()
def topscorers(season_id: int, limit: int = typer.Option(10, "--limit")):
    """Top buteurs d'une saison (hors c.s.c.)."""
    async def _run():
        async with AsyncSessionLocal() as session:
            if not await _ensure_season_exists(session, season_id):
                typer.echo(f"❌ Saison {season_id} inexistante.")
                return

            q = (
                select(Player.name, func.count(Goal.id).label("goals"))
                .join(Goal, Goal.player_id == Player.id)
                .join(Match, Match.id == Goal.match_id)
                .join(Fixture, Fixture.id == Match.fixture_id)
                .where(Fixture.season_id == season_id, Goal.is_own_goal.is_(False))
                .group_by(Player.id, Player.name)
                .order_by(func.count(Goal.id).desc(), Player.name.asc())
                .limit(limit)
            )
            rows = (await session.execute(q)).all()
            if not rows:
                typer.echo("ℹ️ Aucun but enregistré pour cette saison.")
                return

            print(f"Top {limit} buteurs — saison {season_id}")
            print("-------------------------------------")
            for i, (name, goals) in enumerate(rows, start=1):
                print(f"{i:>2}. {name:<22} {goals} but(s)")

    run_async(_run())


@app.command("create-season")
def create_season(
    year: str = typer.Argument(..., help="Libellé de la saison, ex: 2019/2020"),
    league_id: int = typer.Option(1, "--league-id", "-l", help="ID de la ligue (défaut 1)"),
):
    """Crée une saison rattachée à une ligue existante."""
    async def _run():
        async with AsyncSessionLocal() as session:
            s = Season(year=year, league_id=league_id)
            session.add(s)
            await session.commit()
            await session.refresh(s)
            typer.echo(f"✅ Saison créée: id={s.id}, year={s.year}, league_id={s.league_id}")

    run_async(_run())


if __name__ == "__main__":
    app()
