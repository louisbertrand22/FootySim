from sqlalchemy import Integer, String, ForeignKey
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base

if TYPE_CHECKING:
    from .season import Season
    from .player import Player
    from .stadium import Stadium


class Club(Base):
    __tablename__ = "club"

    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("season.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    budget: Mapped[int] = mapped_column(Integer, default=0)
    stadium_id: Mapped[int | None] = mapped_column(ForeignKey("stadium.id"))

    # Relations
    season: Mapped["Season"] = relationship(
        back_populates="clubs"
    )  # ← doit matcher Season.clubs
    stadium: Mapped["Stadium"] = relationship()
    players: Mapped[list["Player"]] = relationship(
        back_populates="club", cascade="all, delete-orphan"
    )
