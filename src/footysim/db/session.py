# src/footysim/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .base import Base
from ..core.config import settings

engine = create_async_engine(
    settings.database_url, echo=settings.echo_sql, pool_pre_ping=True
)
AsyncSessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def init_models() -> None:
    # import src.footysim.models  # charge tous les modèles via models/__init__.py
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
