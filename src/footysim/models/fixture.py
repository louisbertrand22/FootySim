from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Date, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base

if TYPE_CHECKING:
    from .season import Season
    from .match import Match


class Fixture(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("season.id", ondelete="CASCADE"))
    round: Mapped[int] = mapped_column(Integer)
    date: Mapped[date] = mapped_column(Date)
    home_club_id: Mapped[int] = mapped_column(ForeignKey("club.id"))
    away_club_id: Mapped[int] = mapped_column(ForeignKey("club.id"))

    season: Mapped["Season"] = relationship(back_populates="fixtures")
    match: Mapped[Optional["Match"]] = (
        relationship(  # <- ICI: Optional[...] au lieu de "| None"
            uselist=False,
            back_populates="fixture",
        )
    )

    __table_args__ = (
        UniqueConstraint(
            "season_id", "round", "home_club_id", "away_club_id", name="uq_fixture"
        ),
    )
