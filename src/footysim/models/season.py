from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base

if TYPE_CHECKING:
    from .league import League
    from .club import Club
    from .fixture import Fixture


class Season(Base):
    __tablename__ = "season"

    id: Mapped[int] = mapped_column(primary_key=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("league.id"), nullable=False)
    # Libellé type "2019/2020" ⇒ String
    year: Mapped[str] = mapped_column(String(20), nullable=False)

    # Relations
    league: Mapped["League"] = relationship(back_populates="seasons")
    clubs: Mapped[list["Club"]] = relationship(
        back_populates="season", cascade="all, delete-orphan"
    )
    fixtures: Mapped[list["Fixture"]] = relationship(
        back_populates="season", cascade="all, delete-orphan"
    )
