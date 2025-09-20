# src/footysim/cli.py
from __future__ import annotations

import asyncio
from datetime import date
import inspect
from typing import Optional, Dict

import typer
from sqlalchemy import select, delete, outerjoin, func, desc
from sqlalchemy.orm import aliased
from sqlalchemy import case

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


@app.command()
def info():
    """Affiche toutes les commandes disponibles avec leur description."""
    typer.echo("\n📌 Commandes disponibles :\n")

    # Récupère et trie proprement (par nom affiché)
    def display_name(ci: typer.models.CommandInfo) -> str:
        if ci.name:
            return ci.name
        if ci.callback:
            return ci.callback.__name__.replace("_", "-")
        return "<commande>"

    items = sorted(app.registered_commands, key=display_name)

    for ci in items:
        name = display_name(ci)
        # Help: priorité à ci.help, sinon docstring du callback
        help_text = ci.help
        if not help_text and ci.callback:
            help_text = inspect.getdoc(ci.callback)
        help_text = help_text.strip() if help_text else "(pas de description)"
        # largeur fixe seulement si name n'est pas None
        typer.echo(f"- {name:<20} {help_text}")

    typer.echo("\nAstuce : utilise `--help` après une commande pour plus de détails.")
    


@app.command()
def match(match_id: int):
    """Affiche le détail d'un match (score, clubs, buteurs avec minute si dispo)."""
    from .models.goal import Goal

    async def _run():
        async with AsyncSessionLocal() as session:
            Home = aliased(Club)
            Away = aliased(Club)

            # Match + Fixture + Clubs (home/away via alias) en une seule requête
            row = (
                await session.execute(
                    select(
                        Match.id.label("match_id"),
                        Fixture.date,
                        Home.name.label("home_name"),
                        Away.name.label("away_name"),
                        Match.home_goals,
                        Match.away_goals,
                    )
                    .join(Fixture, Match.fixture_id == Fixture.id)
                    .join(Home, Home.id == Fixture.home_club_id)
                    .join(Away, Away.id == Fixture.away_club_id)
                    .where(Match.id == match_id)
                )
            ).first()

            if not row:
                typer.echo(f"Aucun match trouvé avec id={match_id}")
                return

            typer.echo(f"\n📅 {row.date} — Match #{row.match_id}")
            typer.echo(f"{row.home_name} {row.home_goals}–{row.away_goals} {row.away_name}")

            goals = (
                await session.execute(
                    select(
                        Goal.minute,
                        Player.name,
                        Goal.is_own_goal,
                    )
                    .join(Player, Player.id == Goal.player_id)
                    .where(Goal.match_id == match_id)
                    .order_by(Goal.minute.is_(None), Goal.minute.asc(), Goal.id.asc())
                )
            ).all()

            if goals:
                typer.echo("\n⚽ Buteurs :")
                for minute, name, own_goal in goals:
                    m = f"{minute}' " if minute is not None else ""
                    if own_goal:
                        typer.echo(f"- {m}CSC {name}")
                    else:
                        typer.echo(f"- {m}{name}")
            else:
                typer.echo("\n⚽ Aucun but enregistré pour ce match.")

    asyncio.run(_run())
    
@app.command()
def player(
    player_id: int = typer.Argument(..., help="ID du joueur"),
    season_id: int | None = typer.Option(
        None, "--season-id", "-s", help="Filtrer les stats sur cette saison"
    ),
    limit: int = typer.Option(10, "--limit", "-n", help="Nombre de buts récents à afficher"),
):
    """Affiche les détails d'un joueur (profil, club, stats de buts et liste des derniers buts)."""
    from .models.goal import Goal

    async def _run():
        async with AsyncSessionLocal() as session:
            # 1) Profil du joueur + club
            row = (
                await session.execute(
                    select(
                        Player.id,
                        Player.name,
                        Player.age,
                        Player.position,
                        Player.pace,
                        Player.shot,
                        Player.pass_,
                        Player.defend,
                        Club.name.label("club_name"),
                        Club.season_id.label("club_season_id"),
                    )
                    .join(Club, Club.id == Player.club_id, isouter=True)
                    .where(Player.id == player_id)
                )
            ).first()

            if not row:
                typer.echo(f"Aucun joueur trouvé avec id={player_id}")
                return

            # 2) Totaux de buts (filtrés ou non par saison)
            q_stats = (
                select(
                    func.count(Goal.id).label("total_goals"),
                    func.sum(case((Goal.is_own_goal, 1), else_=0)).label("own_goals"),
                )
                .join(Match, Match.id == Goal.match_id)
                .join(Fixture, Fixture.id == Match.fixture_id)
                .where(Goal.player_id == player_id)
            )
            if season_id is not None:
                q_stats = q_stats.where(Fixture.season_id == season_id)

            stats = (await session.execute(q_stats)).one()
            total_goals = int(stats.total_goals or 0)
            own_goals = int(stats.own_goals or 0)
            normal_goals = total_goals - own_goals

            # 3) Liste des derniers buts avec minute, date, adversaire
            Home = aliased(Club)
            Away = aliased(Club)
            q_goals = (
                select(
                    Fixture.date,
                    Goal.minute,
                    Goal.is_own_goal,
                    Home.name.label("home_name"),
                    Away.name.label("away_name"),
                )
                .join(Match, Match.id == Goal.match_id)
                .join(Fixture, Fixture.id == Match.fixture_id)
                .join(Home, Home.id == Fixture.home_club_id)
                .join(Away, Away.id == Fixture.away_club_id)
                .where(Goal.player_id == player_id)
                .order_by(Fixture.date.desc(), Goal.minute.is_(None), Goal.minute.desc(), Goal.id.desc())
                .limit(limit)
            )
            if season_id is not None:
                q_goals = q_goals.where(Fixture.season_id == season_id)

            goals_rows = (await session.execute(q_goals)).all()

            # 4) Affichage
            typer.echo(f"\n🧑 Joueur #{row.id} — {row.name}")
            typer.echo(f"   Club : {row.club_name or 'Sans club'}")
            typer.echo(f"   Âge  : {row.age} | Poste : {row.position}")
            typer.echo(f"   Attributs — Pace:{row.pace} Shot:{row.shot} Pass:{row.pass_} Def:{row.defend}")

            scope = f"saison {season_id}" if season_id is not None else "toutes saisons"
            typer.echo(f"\n📊 Stats ({scope})")
            typer.echo(f"   Buts : {normal_goals} | CSC : {own_goals} | Total événements but : {total_goals}")

            typer.echo(f"\n⚽ Derniers buts ({min(limit, len(goals_rows))})")
            if not goals_rows:
                typer.echo("   Aucun but enregistré.")
            else:
                for d, minute, is_og, home, away in goals_rows:
                    m = f"{minute}' " if minute is not None else ""
                    fixture_str = f"{home} vs {away}"
                    if is_og:
                        typer.echo(f"   - {d} — {m}CSC ({fixture_str})")
                    else:
                        typer.echo(f"   - {d} — {m}{fixture_str}")

    asyncio.run(_run())
    
@app.command("best-players")
def best_players(
    season_id: int | None = typer.Option(
        None, "--season-id", "-s", help="Filtre par saison (ID). Laisse vide pour toutes."
    ),
    position: str | None = typer.Option(
        None, "--position", "-p", help="Filtrer par poste: GK/DF/MF/FW"
    ),
    limit: int = typer.Option(20, "--limit", "-n", min=1, max=200, help="Nombre de joueurs à afficher"),
):
    """
    Affiche les meilleurs joueurs par note globale (moyenne pace/shot/pass/defend).
    """

    async def _run():
        async with AsyncSessionLocal() as session:
            # Expression SQL de la note globale
            overall_expr = (
                (Player.pace + Player.shot + Player.pass_ + Player.defend) / 4
            ).label("overall")

            q = (
                select(
                    Player.id,
                    Player.name,
                    Player.age,
                    Player.position,
                    Club.name.label("club"),
                    overall_expr,
                )
                .select_from(Player)
                .join(Club, Club.id == Player.club_id, isouter=True)
            )

            if season_id is not None:
                q = q.where(Club.season_id == season_id)

            if position:
                pos = position.upper().strip()
                if pos not in {"GK", "DF", "MF", "FW"}:
                    typer.echo("Poste invalide. Utilise GK/DF/MF/FW.")
                    return
                q = q.where(Player.position == pos)

            q = q.order_by(desc(overall_expr), Player.name.asc()).limit(limit)

            rows = (await session.execute(q)).all()
            if not rows:
                typer.echo("Aucun joueur trouvé avec ces critères.")
                return

            title = f"Meilleurs joueurs (top {limit})"
            if season_id is not None:
                title += f" — saison {season_id}"
            if position:
                title += f" — poste {position.upper()}"
            print(title)
            print("-" * len(title))

            header = f"{'#':>2}  {'Joueur':<22} {'Âge':>3} {'Pos':>3}  {'Club':<18} {'OVR':>3}"
            line = "-" * len(header)
            print(header)
            print(line)

            for i, (pid, name, age, pos, club, overall) in enumerate(rows, start=1):
                club_disp = club or "(libre)"
                ovr = int(overall or 0)
                print(f"{i:>2}  {name:<22} {age:>3} {pos:>3}  {club_disp:<18} {ovr:>3}")

    asyncio.run(_run())
    
@app.command("best-club")
def best_club(
    season_id: int = typer.Argument(..., help="ID de la saison"),
    limit: int = typer.Option(10, "--limit", "-n", min=1, max=50, help="Nombre de clubs à afficher"),
    metric: str = typer.Option(
        "overall",
        "--metric",
        "-m",
        help="Critère: overall | pace | shot | pass | defend | age",
    ),
):
    """
    Classe les clubs par qualité moyenne de l'effectif (moyenne des attributs joueurs).
    Par défaut: overall moyen = (pace+shot+pass+defend)/4.
    """
    valid = {"overall", "pace", "shot", "pass", "defend", "age"}
    if metric not in valid:
        raise typer.BadParameter(f"metric doit être dans {sorted(valid)}")

    async def _run():
        async with AsyncSessionLocal() as session:
            # Map club_id -> nom (filtré sur la saison)
            club_rows = await session.execute(
                select(Club.id, Club.name).where(Club.season_id == season_id)
            )
            clubs = dict(club_rows.all())
            if not clubs:
                print("Aucun club pour cette saison.")
                return

            # Construire l'expression SQL selon la métrique
            # NB: on calcule l'overall côté SQL (hybrid_property non utilisable dans AVG SQL)
            if metric == "overall":
                expr = (Player.pace + Player.shot + Player.pass_ + Player.defend) / 4.0
                label = "overall_avg"
            elif metric == "pace":
                expr, label = Player.pace, "pace_avg"
            elif metric == "shot":
                expr, label = Player.shot, "shot_avg"
            elif metric == "pass":
                expr, label = Player.pass_, "pass_avg"
            elif metric == "defend":
                expr, label = Player.defend, "defend_avg"
            else:  # age
                expr, label = Player.age, "age_avg"

            q = (
                select(
                    Club.id,
                    Club.name,
                    func.avg(expr).label(label),
                    func.count(Player.id).label("players"),
                )
                .join(Player, Player.club_id == Club.id, isouter=True)
                .where(Club.season_id == season_id)
                .group_by(Club.id, Club.name)
                .order_by(getattr(func.avg(expr), "desc")())  # tri décroissant
            )

            rows = (await session.execute(q)).all()
            if not rows:
                print("Aucun joueur trouvé pour calculer les moyennes.")
                return

            # Affichage
            pretty_metric = {"overall": "Overall", "pace": "Pace", "shot": "Shot",
                             "pass": "Pass", "defend": "Defend", "age": "Âge"}[metric]
            print(f"🏅 Meilleurs clubs — saison {season_id} (métrique: {pretty_metric})")
            header = f"{'#':>2}  {'Club':<24} {'Jou.':>4}  {pretty_metric:>8}"
            print(header)
            print("-" * len(header))

            for i, (club_id, name, avg_val, players) in enumerate(rows[:limit], start=1):
                avg_str = f"{avg_val:.2f}" if avg_val is not None else "—"
                print(f"{i:>2}  {name:<24} {players:>4}  {avg_str:>8}")

    asyncio.run(_run())


    
if __name__ == "__main__":
    app()
