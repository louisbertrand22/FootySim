from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base

class Season(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("league.id", ondelete="CASCADE"))
    year: Mapped[int] = mapped_column(Integer)

    league: Mapped["League"] = relationship(back_populates="seasons")
    clubs: Mapped[list["Club"]] = relationship(back_populates="season")
    fixtures: Mapped[list["Fixture"]] = relationship(back_populates="season")
