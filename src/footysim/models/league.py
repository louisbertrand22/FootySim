from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy import String
from sqlalchemy.orm import mapped_column
from ..db.base import Base

if TYPE_CHECKING:
    from .season import Season


class League(Base):
    __tablename__ = "league"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    country: Mapped[str] = mapped_column(String(80))

    seasons: Mapped[list["Season"]] = relationship(
        back_populates="league", cascade="all, delete-orphan"
    )
