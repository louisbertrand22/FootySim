from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base

class League(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    country: Mapped[str] = mapped_column(String(80))

    seasons: Mapped[list["Season"]] = relationship(back_populates="league")
