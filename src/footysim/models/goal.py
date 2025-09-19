# src/footysim/models/goal.py
from sqlalchemy import Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from ..db.base import Base


class Goal(Base):
    __tablename__ = "goal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("match.id", ondelete="CASCADE"), nullable=False
    )
    club_id: Mapped[int] = mapped_column(
        ForeignKey("club.id", ondelete="CASCADE"), nullable=False
    )
    player_id: Mapped[int] = mapped_column(
        ForeignKey("player.id", ondelete="SET NULL"), nullable=True
    )
    minute: Mapped[int] = mapped_column(Integer, nullable=False)
    is_own_goal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    match = relationship("Match", back_populates="goals")
    player = relationship("Player", back_populates="goals")
