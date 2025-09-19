# src/footysim/models/player.py
from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import String, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from ..db.base import Base

if TYPE_CHECKING:
    from .club import Club
    from .goal import Goal


class Player(Base):
    __tablename__ = "player"

    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int | None] = mapped_column(
        ForeignKey("club.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[str] = mapped_column(String(5), nullable=False)  # GK/DF/MF/FW
    pace: Mapped[int] = mapped_column(Integer, nullable=False)
    shot: Mapped[int] = mapped_column(Integer, nullable=False)
    pass_: Mapped[int] = mapped_column("pass", Integer, nullable=False)
    defend: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relations
    club: Mapped["Club"] = relationship(back_populates="players")
    goals: Mapped[list["Goal"]] = relationship(
        "Goal",
        back_populates="player",
        lazy="selectin",
    )

    @hybrid_property
    def overall(self) -> int:
        return int((self.pace + self.shot + self.pass_ + self.defend) / 4)
