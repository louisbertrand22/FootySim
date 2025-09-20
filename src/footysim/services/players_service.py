from typing import Iterable, Dict, Any
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from footysim.models.player import Player
from footysim.models.club import Club


def _normalize_position(position: str | None) -> str | None:
    if not position:
        return None
    pos = position.upper().strip()
    if pos not in {"GK", "DF", "MF", "FW"}:
        raise ValueError("Poste invalide. Utilise GK/DF/MF/FW.")
    return pos


async def best_players(
    session: AsyncSession,
    *,
    season_id: int | None = None,
    position: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """
    Retourne les meilleurs joueurs par note globale (moyenne pace/shot/pass/defend),
    triés décroissant. Résultat: liste de dicts JSON-friendly.
    """
    pos = _normalize_position(position)

    # note globale
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

    if pos:
        q = q.where(Player.position == pos)

    q = q.order_by(desc(overall_expr), Player.name.asc()).limit(limit)

    rows = (await session.execute(q)).all()

    payload: list[dict] = []
    for i, (pid, name, age, ppos, club, overall) in enumerate(rows, start=1):
        payload.append(
            {
                "rank": i,
                "id": pid,
                "name": name,
                "age": age,
                "position": ppos,
                "club": club or "(libre)",
                "overall": int(overall or 0),
            }
        )

    return payload
