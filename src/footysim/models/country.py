from typing import TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base

if TYPE_CHECKING:
    from .stadium import Stadium


class Country(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(3), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)

    stadiums: Mapped[list["Stadium"]] = relationship(back_populates="country")
