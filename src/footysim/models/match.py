# src/footysim/models/match.py
from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base

if TYPE_CHECKING:
    from .fixture import Fixture
    from .goal import Goal


class Match(Base):
    __tablename__ = "match"

    id: Mapped[int] = mapped_column(primary_key=True)
    fixture_id: Mapped[int] = mapped_column(
        ForeignKey("fixture.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    home_goals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    away_goals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relations
    fixture: Mapped["Fixture"] = relationship(back_populates="match")
    goals: Mapped[list["Goal"]] = relationship(
        "Goal",
        back_populates="match",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
