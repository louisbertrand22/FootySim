# src/footysim/models/fixture.py
from __future__ import annotations
from datetime import date as _date, datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import ForeignKey, Integer, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from ..db.base import Base

if TYPE_CHECKING:
    from .season import Season
    from .match import Match

class Fixture(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("season.id", ondelete="CASCADE"))
    round: Mapped[int] = mapped_column(Integer)
    date: Mapped[_date] = mapped_column(Date, nullable=False)

    home_club_id: Mapped[int] = mapped_column(ForeignKey("club.id"))
    away_club_id: Mapped[int] = mapped_column(ForeignKey("club.id"))

    season: Mapped["Season"] = relationship(back_populates="fixtures")
    match: Mapped[Optional["Match"]] = relationship(
        uselist=False,
        back_populates="fixture",
        cascade="all, delete-orphan",
    )

    @validates("date")
    def _coerce_date(self, key, value):
        # Accepte "YYYY-MM-DD", datetime, ou date
        if isinstance(value, str):
            return _date.fromisoformat(value)
        if isinstance(value, datetime):
            return value.date()
        return value
