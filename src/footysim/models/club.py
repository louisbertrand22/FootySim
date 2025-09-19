from typing import Optional
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base

class Club(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("season.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    budget: Mapped[float] = mapped_column(default=50_000_000.0)
    stadium_id: Mapped[Optional[int]] = mapped_column(ForeignKey("stadium.id", ondelete="SET NULL"))

    season: Mapped["Season"] = relationship(back_populates="clubs")
    players: Mapped[list["Player"]] = relationship(back_populates="club")
    stadium: Mapped[Optional["Stadium"]] = relationship(back_populates="clubs")
