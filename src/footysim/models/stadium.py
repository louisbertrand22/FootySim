from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base

if TYPE_CHECKING:
    from .country import Country
    from .club import Club


class Stadium(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    country_id: Mapped[int] = mapped_column(
        ForeignKey("country.id", ondelete="RESTRICT")
    )
    name: Mapped[str] = mapped_column(String(120), unique=True)
    capacity: Mapped[int] = mapped_column(Integer)
    city: Mapped[str] = mapped_column(String(80))

    country: Mapped["Country"] = relationship(back_populates="stadiums")
    clubs: Mapped[list["Club"]] = relationship(back_populates="stadium")
