from datetime import date
from typing import TYPE_CHECKING, Optional
from sqlalchemy import ForeignKey, Date, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base

if TYPE_CHECKING:
    from .player import Player
    from .club import Club


class Transfer(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("player.id", ondelete="CASCADE"), index=True
    )
    from_club_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("club.id", ondelete="SET NULL")
    )
    to_club_id: Mapped[int] = mapped_column(ForeignKey("club.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date)
    fee: Mapped[float] = mapped_column(Numeric(14, 2), default=0)

    player: Mapped["Player"] = relationship()
    from_club: Mapped[Optional["Club"]] = relationship(foreign_keys=[from_club_id])
    to_club: Mapped["Club"] = relationship(foreign_keys=[to_club_id])
