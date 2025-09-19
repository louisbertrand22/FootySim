# tests/conftest.py
import pytest_asyncio
from src.footysim.db.base import Base
from src.footysim.db.session import engine, AsyncSessionLocal
# import src.footysim.models  # important : charge tous les modèles


# Crée/Reset le schéma une fois pour toute la session de tests
@pytest_asyncio.fixture(scope="session", autouse=True)
async def _setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


# Fournit une AsyncSession pour chaque test
@pytest_asyncio.fixture
async def session():
    async with AsyncSessionLocal() as s:
        yield s
